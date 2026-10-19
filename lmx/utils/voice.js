/**
 * 语音对话工具模块
 *
 * 后端提供基于 Vosk 的本地离线语音识别（STT），接口：
 *   POST /api/ai/voice/chat   form-data: file(WAV) + session_id?  -> { recognized_text, answer|narrative, session_id }
 *   GET  /api/ai/voice/status -> { available: bool }
 *
 * Vosk 要求 WAV 格式（单声道 16bit PCM，采样率任意，后端会自动重采样到 16k）。
 *
 * 平台差异：
 *  - H5（web）：uni-app 的 recorderManager 在 H5 走的是浏览器 MediaRecorder，不能直接产出 WAV，
 *    因此这里用 Web Audio(ScriptProcessor) 抓取原始 PCM 再手动编码成 WAV。
 *  - App（app-plus）：uni.getRecorderManager 支持 format:'wav'，直接产出 WAV 文件。
 *  - 小程序（mp-weixin 等）：录音格式为 aac/mp3/silk，无法被 Vosk 识别，故禁用语音输入。
 *
 * TTS（AI 文字转语音）在前端用浏览器 speechSynthesis 实现（仅 H5 可用，App 无原生能力则静默跳过）。
 */

import {
	getToken
} from '@/utils/auth'
import {
	getApiBaseUrl
} from '@/utils/config'

/* ============ 平台检测 ============ */
function getPlatform() {
	// 优先运行时字段
	try {
		const info = uni.getSystemInfoSync()
		if (info.uniPlatform) return info.uniPlatform // 'web' | 'app-plus' | 'mp-weixin' | 'mp-alipay' ...
		if (info.platform === 'web') return 'web'
	} catch (e) {
		// ignore
	}
	// 编译期兜底
	if (typeof process !== 'undefined' && process.env && process.env.UNI_PLATFORM) {
		return process.env.UNI_PLATFORM
	}
	return 'unknown'
}

/** 当前平台是否支持语音输入（即能产出 WAV 给 Vosk） */
export function isVoiceSupported() {
	const p = getPlatform()
	return p === 'web' || p === 'app-plus'
}

/* ============ H5：Web Audio 录制并编码 WAV ============ */
function writeString(view, offset, str) {
	for (let i = 0; i < str.length; i++) {
		view.setUint8(offset + i, str.charCodeAt(i))
	}
}

function encodeWav(chunks, sampleRate) {
	let length = 0
	for (const c of chunks) length += c.length

	const samples = new Float32Array(length)
	let offset = 0
	for (const c of chunks) {
		samples.set(c, offset)
		offset += c.length
	}

	const bytesPerSample = 2
	const blockAlign = 1 * bytesPerSample
	const dataSize = samples.length * bytesPerSample
	const buffer = new ArrayBuffer(44 + dataSize)
	const view = new DataView(buffer)

	writeString(view, 0, 'RIFF')
	view.setUint32(4, 36 + dataSize, true)
	writeString(view, 8, 'WAVE')
	writeString(view, 12, 'fmt ')
	view.setUint32(16, 16, true) // PCM 子块大小
	view.setUint16(20, 1, true) // 音频格式 = PCM
	view.setUint16(22, 1, true) // 声道数 = 1（单声道）
	view.setUint32(24, sampleRate, true)
	view.setUint32(28, sampleRate * blockAlign, true) // 字节率
	view.setUint16(32, blockAlign, true)
	view.setUint16(34, 16, true) // 位深 = 16bit
	writeString(view, 36, 'data')
	view.setUint32(40, dataSize, true)

	let pos = 44
	for (let i = 0; i < samples.length; i++) {
		let s = Math.max(-1, Math.min(1, samples[i]))
		view.setInt16(pos, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
		pos += 2
	}
	return new Blob([view], {
		type: 'audio/wav'
	})
}

function createH5Recorder() {
	let audioContext = null
	let stream = null
	let sourceNode = null
	let processorNode = null
	let recording = false
	const chunks = []

	function start() {
		return new Promise(async (resolve, reject) => {
			try {
				const AC = window.AudioContext || window.webkitAudioContext
				if (!AC) {
					reject(new Error('当前浏览器不支持 Web Audio'))
					return
				}
				audioContext = new AC()
				stream = await navigator.mediaDevices.getUserMedia({
					audio: true
				})
				sourceNode = audioContext.createMediaStreamSource(stream)
				// 单声道输入/输出，bufferSize 4096
				processorNode = audioContext.createScriptProcessor(4096, 1, 1)
				processorNode.onaudioprocess = (e) => {
					if (!recording) return
					const input = e.inputBuffer.getChannelData(0)
					chunks.push(new Float32Array(input))
				}
				sourceNode.connect(processorNode)
				// 部分浏览器要求连到 destination 才会触发 onaudioprocess
				processorNode.connect(audioContext.destination)
				recording = true
				resolve()
			} catch (err) {
				// 常见：用户拒绝麦克风权限 / 非安全上下文(非 localhost/https)
				reject(err)
			}
		})
	}

	function stop() {
		return new Promise((resolve) => {
			recording = false
			const sampleRate = audioContext ? audioContext.sampleRate : 44100
			try {
				if (stream) stream.getTracks().forEach((t) => t.stop())
			} catch (e) {}
			try {
				if (processorNode) processorNode.disconnect()
			} catch (e) {}
			try {
				if (sourceNode) sourceNode.disconnect()
			} catch (e) {}
			try {
				if (audioContext) audioContext.close()
			} catch (e) {}
			const wav = encodeWav(chunks, sampleRate)
			resolve({
				type: 'blob',
				blob: wav,
				path: null
			})
		})
	}

	return {
		start,
		stop
	}
}

/* ============ App：原生 recorderManager 录制 WAV ============ */
function createAppRecorder() {
	const rm = uni.getRecorderManager()
	let filePath = ''
	let stoppedResolve = null

	rm.onStop((res) => {
		filePath = res.tempFilePath
		if (stoppedResolve) stoppedResolve({
			type: 'path',
			blob: null,
			path: filePath
		})
	})

	function start() {
		return new Promise((resolve, reject) => {
			try {
				rm.start({
					duration: 60000,
					format: 'wav',
					sampleRate: 16000,
					numberOfChannels: 1
				})
				// recorderManager 没有 start 回调，稍候即视为已开始
				setTimeout(resolve, 60)
			} catch (e) {
				reject(e)
			}
		})
	}

	function stop() {
		return new Promise((resolve) => {
			stoppedResolve = resolve
			rm.stop()
		})
	}

	return {
		start,
		stop
	}
}

/* ============ 统一录制控制 ============ */
let currentRecorder = null

/** 开始录音（按平台选择实现） */
export async function startVoiceRecord() {
	const p = getPlatform()
	if (p === 'web') {
		currentRecorder = createH5Recorder()
	} else if (p === 'app-plus') {
		currentRecorder = createAppRecorder()
	} else {
		throw new Error('UNSUPPORTED_PLATFORM')
	}
	await currentRecorder.start()
}

/** 停止录音，返回 { type:'blob'|'path', blob, path } */
export async function stopVoiceRecord() {
	if (!currentRecorder) return null
	const result = await currentRecorder.stop()
	currentRecorder = null
	return result
}

/* ============ 上传语音到后端 /voice/chat ============ */
function normalizeResponse(res) {
	// res 形如 { statusCode, data }，data 可能是对象或 JSON 字符串
	let data = res.data
	if (typeof data === 'string') {
		try {
			data = JSON.parse(data)
		} catch (e) {
			data = {
				code: res.statusCode || 0,
				message: data,
				data: null
			}
		}
	}
	return {
		statusCode: res.statusCode,
		data
	}
}

function mapUploadError(err) {
	return {
		statusCode: err && err.statusCode ? err.statusCode : 0,
		errMsg: (err && err.errMsg) || '语音上传失败',
		data: err && err.data ? err.data : null
	}
}

/**
 * 上传录音并获取 AI 回复
 * @param {Object} param
 * @param {Blob}   [param.blob]  H5 录音得到的 WAV Blob
 * @param {string} [param.path]  App 录音得到的 WAV 文件路径
 * @param {number|null} [param.session_id] 会话 id
 * @returns {Promise<{statusCode,data}>} 归一化响应
 */
export function uploadVoiceChat({
	blob,
	path,
	session_id
} = {}) {
	return new Promise((resolve, reject) => {
		const token = getToken()
		const url = getApiBaseUrl() + '/api/ai/voice/chat'
		const header = {}
		if (token) header['Authorization'] = `Bearer ${token}`

		const p = getPlatform()

		if (p === 'app-plus') {
			// App 端：uni.uploadFile
			const formData = {}
			if (session_id) formData.session_id = Number(session_id)
			uni.uploadFile({
				url,
				filePath: path,
				name: 'file',
				formData,
				header,
				success: (res) => resolve(normalizeResponse(res)),
				fail: (err) => reject(mapUploadError(err))
			})
		} else {
			// H5 端：用 XHR + FormData 上传 Blob
			const fd = new FormData()
			fd.append('file', blob, 'voice.wav')
			if (session_id) fd.append('session_id', Number(session_id))
			const xhr = new XMLHttpRequest()
			xhr.open('POST', url)
			if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
			xhr.responseType = 'json'
			xhr.onload = () => {
				if (xhr.status === 200) {
					resolve({
						statusCode: 200,
						data: xhr.response || {}
					})
				} else {
					reject(mapUploadError({
						statusCode: xhr.status,
						data: xhr.response,
						errMsg: '语音上传失败'
					}))
				}
			}
			xhr.onerror = () =>
				reject(mapUploadError({
					errMsg: '网络错误，无法连接语音服务'
				}))
			xhr.send(fd)
		}
	})
}

/* ============ TTS：前端朗读（仅 H5 浏览器支持） ============ */
export function isTTSAvailable() {
	try {
		return typeof window !== 'undefined' && !!window.speechSynthesis
	} catch (e) {
		return false
	}
}

/** 朗读文本；返回是否成功触发 */
export function speakText(text, {
	lang = 'zh-CN',
	rate = 1.0,
	pitch = 1.0,
	onEnd = null
} = {}) {
	if (!text) return false
	try {
		if (!window.speechSynthesis) return false
		window.speechSynthesis.cancel()
		const u = new SpeechSynthesisUtterance(text)
		u.lang = lang
		u.rate = rate
		u.pitch = pitch
		if (typeof onEnd === 'function') {
			u.onend = onEnd
			u.onerror = onEnd
		}
		window.speechSynthesis.speak(u)
		return true
	} catch (e) {
		return false
	}
}

export function stopSpeak() {
	try {
		if (typeof window !== 'undefined' && window.speechSynthesis) {
			window.speechSynthesis.cancel()
		}
	} catch (e) {}
}

export default {
	isVoiceSupported,
	startVoiceRecord,
	stopVoiceRecord,
	uploadVoiceChat,
	isTTSAvailable,
	speakText,
	stopSpeak
}
