<template>
	<view class="chat-container">
		<!-- 顶部状态栏 + 图标按钮 -->
		<view class="status-bar">
			<view class="location-brief">
				<text class="location-name">AI助手</text>
			</view>
			<view class="header-icons">
				<uni-icons type="compose" size="20" color="white" class="icon-btn" @click="clearNewChat"></uni-icons>
				<uni-icons type="list" size="20" color="white" class="icon-btn"
					@click="()=>{loadHistoryList(); showHistoryPanel=!showHistoryPanel}"></uni-icons>
			</view>
		</view>

		<!-- 历史对话面板 -->
		<view class="history-panel" v-if="showHistoryPanel">
			<view class="history-item" v-for="(item,idx) in historyList" :key="idx">
				<view class="history-left" @click="switchHistory(item,idx)">
					<text class="title">{{ item.title || '未命名对话' }}</text>
					<!-- <text class="time">{{ item.time }}</text> -->
				</view>
				<view class="del-btn" @click.stop="delSession(item,idx)">
					<uni-icons type="trash" size="18" color="#999"></uni-icons>

				</view>
			</view>
			<view class="empty-history" v-if="historyList.length === 0">
				暂无历史对话
			</view>
		</view>

		<!-- 对话列表 -->
		<scroll-view class="chat-list" scroll-y :scroll-into-view="scrollIntoViewId" :scroll-with-animation="true">
			<view class="msg-item ai" v-if="messages.length === 0">
				<view class="msg-content">
					你好呀 😊 我是你的专属旅行助手，有任何旅行问题都可以问我：
				</view>
			</view>

			<view class="msg-item" :class="{ai: item.role === 'system', user: item.role === 'user'}"
				v-for="(item, idx) in messages" :key="idx" :id="'msg-' + idx">
				<view class="msg-content">
					<view class="loading-container" v-if="item.loading">
						<view class="loading-dot"></view>
						<view class="loading-dot"></view>
						<view class="loading-dot"></view>
						<view class="loading-dot"></view>
						<view class="loading-dot"></view>
					</view>
					<view v-else class="msg-body">
						<text class="msg-text">{{ item.content }}</text>
						<view v-if="item.role === 'system'" class="speak-btn" :class="{active: speakingIndex === idx}"
							@click="toggleSpeak(idx, item.content)" hover-class="speak-btn-hover">
							<uni-icons type="sound" size="18"
								:color="speakingIndex === idx ? '#2E86DE' : '#94a3b8'"></uni-icons>
						</view>
					</view>
					<!-- 行程待确认：先问后存（确认才调 /api/planning/itinerary/save 落库） -->
					<view v-if="item.response_type === 'itinerary' && item.needs_save && !item.saved" class="save-bar">
						<text class="save-bar-tip">要把这份计划添加进你的行程吗？</text>
						<view class="save-bar-actions">
							<button class="save-btn primary" :disabled="item.saving" @click="confirmSaveItinerary(item)">添加到行程</button>
							<button class="save-btn ghost" @click="dismissSave(item)">暂不添加</button>
						</view>
					</view>
					<view v-if="item.response_type === 'itinerary' && item.saved" class="save-done">
						<text>已添加行程</text>
						<text v-if="item.tripId" class="save-done-link" @click="goTripDetail(item.tripId)"> · 查看行程</text>
					</view>
				</view>
			</view>
		</scroll-view>

		<!-- 输入框区域 -->
		<view class="input-box">
			<view class="mic-btn" :class="{recording: isRecording}" @click="toggleVoice"
				hover-class="mic-btn-hover">
				<uni-icons :type="isRecording ? 'micoff-filled' : 'mic'" size="22"
					:color="isRecording ? '#fff' : '#2E86DE'"></uni-icons>
			</view>
			<textarea class="input" v-model="inputContent" placeholder="输入或按住麦克风说出你的问题..."
				confirm-type="send" @confirm="sendMsg"></textarea>
			<button class="send-btn" @click="sendMsg" :disabled="!inputContent.trim()">
				发送
			</button>
		</view>

		<!-- 录音提示 -->
		<view class="voice-hint" v-if="isRecording">
			<view class="voice-pulse"></view>
			<text>正在聆听，点击麦克风结束</text>
		</view>
	</view>
</template>

<script setup>
	import {
		ref,
		watch,
		nextTick,
		onMounted
	} from 'vue'
	import {
		onLoad,
		onShow
	} from '@dcloudio/uni-app'
	import {
		getUserInfo
	} from '@/api/user.js'
	import {
		aiChat,
		getSessions,
		getSessionMessages,
		deleteSession,
		voiceStatus,
		saveItinerary
	} from '@/api/ai.js'
	import {
		isVoiceSupported,
		isTTSAvailable,
		startVoiceRecord,
		stopVoiceRecord,
		uploadVoiceChat,
		speakText,
		stopSpeak
	} from '@/utils/voice.js'
// 原有数据
	const tripContent = ref('')
	const messages = ref([])
	const inputContent = ref('')
	// const scrollTop = ref(0)
	// const isManualScroll = ref(false)
	const isLoading = ref(false)
	const latestItineraryRaw = ref('')

	// 历史对话相关
	const showHistoryPanel = ref(false)
	const historyList = ref([])
	const currentSessionId = ref(null)
	const isNewChat = ref(false) // 标记是否需要创建新会话

	// 语音对话相关
	const isRecording = ref(false) // 是否正在录音
	const voiceSupported = ref(false) // 当前平台是否支持语音输入
	const voiceAvailable = ref(true) // 后端 Vosk 模型是否已加载
	const speakingIndex = ref(null) // 正在朗读的 AI 消息下标；null 表示未朗读

	// 页面滑动
	// const chatScroll = ref(null) // 滚动容器引用
	// const isAtBottom = ref(true) // 标记是否在底部
	const scrollIntoViewId = ref('')
	// 页面打开时自动加载历史对话
	onLoad(() => {
		loadHistoryList()
		get_UserInfo()
	})

	// 进入页面时检查语音能力
	onShow(() => {
		checkVoice()
	})

	// 检查语音输入是否可用（平台 + 后端 Vosk 模型）
	const checkVoice = async () => {
		voiceSupported.value = isVoiceSupported()
		if (!voiceSupported.value) {
			voiceAvailable.value = false
			return
		}
		try {
			const res = await voiceStatus()
			if (res.data && res.data.code === 200 && res.data.data) {
				voiceAvailable.value = res.data.data.available
				if (!voiceAvailable.value) {
					uni.showToast({
						title: '语音模型未加载，已禁用语音输入',
						icon: 'none'
					})
				}
			} else {
				voiceAvailable.value = false
			}
		} catch (e) {
			// 状态接口异常时不阻断文字输入，但保守禁用语音避免误触
			voiceAvailable.value = false
		}
	}

	// 获取会话列表
	const loadHistoryList = async () => {
		try {
			// 后端基于 token 自动识别当前用户
			const res = await getSessions()

			if (res.data.code === 200) {
				historyList.value = (res.data.data.sessions || []).map(session => ({
					id: session.session_id,
					title: session.title || '未命名会话',
					time: formatTime(session.update_time),
					trip_id: session.trip_id
				}))
			}
		} catch (err) {
			console.error('加载会话失败：', err)
		}
	}

	// 删除会话
	const delSession = async (item, idx) => {
		uni.showModal({
			title: '删除会话',
			content: '确定要删除这条对话记录吗？',
			success: async (res) => {
				if (!res.confirm) return;
				try {
						const result = await deleteSession(item.id)

						if (result.data.code === 200) {
						// 前端移除
						historyList.value.splice(idx, 1)
						// 如果删的是当前正在聊天的会话，清空聊天
						if (currentSessionId.value === item.id) {
							messages.value = []
							currentSessionId.value = null
						}
						uni.showToast({
							title: '删除成功'
						})
					} else {
						uni.showToast({
							title: result.data.message || '删除失败',
							icon: 'none'
						})
					}
				} catch (err) {
					console.error('删除会话失败：', err)
					uni.showToast({
						title: '网络异常',
						icon: 'none'
					})
				}
			}
		})
	}

	// 时间格式化
	const formatTime = (isoString) => {
		if (!isoString) return ''
		const date = new Date(isoString)
		const now = new Date()
		const diff = now - date
		if (diff < 24 * 60 * 60 * 1000) {
			return date.toLocaleTimeString('zh-CN', {
				hour: '2-digit',
				minute: '2-digit'
			})
		}
		return date.toLocaleDateString('zh-CN', {
			month: 'short',
			day: 'numeric'
		})
	}

	// 加载会话消息
	const loadSessionMessages = async (sessionId) => {
		try {
			const res = await getSessionMessages(sessionId)

			if (res.data.code === 200) {
				messages.value = (res.data.data.messages || []).map(msg => ({
					role: msg.role,
					content: parseMessageContent(msg.content, msg.role)
				}))
				currentSessionId.value = sessionId
				showHistoryPanel.value = false
				nextTick(() => {
					scrollToBottom()
				})
				console.log('消息列表：', messages.value)
			}
		} catch (err) {
			console.error('加载消息失败：', err)
		}
	}

	// 解析AI消息（历史消息中 AI 角色经 api 层已归一化为 'system'）
	const parseMessageContent = (content, role) => {
		if (role !== 'system') return content
		try {
			const aiData = JSON.parse(content)
			// 兼容后端存储的多种结构：{ response_type, data:{ narrative|answer } } 或 { narrative, answer }
			const inner = aiData.data || aiData
			if (aiData.response_type === 'itinerary' || inner.narrative) return inner.narrative || content
			if (aiData.response_type === 'question_answer' || inner.answer) return inner.answer || content
			return content
		} catch (e) {
			return content
		}
	}

	// 新建对话
	const clearNewChat = () => {
		uni.showModal({
			title: '新建对话',
			content: '确定要创建一个新的对话吗？',
			success: (res) => {
				if (res.confirm) {
					// 清空前端消息列表
					messages.value = []

					// 重置当前会话 ID
					currentSessionId.value = null

					// 【关键】标记下次发送时需要创建新会话
					isNewChat.value = true

					// 关闭历史面板
					showHistoryPanel.value = false

					uni.showToast({
						title: '已新建对话',
						icon: 'success'
					})
				}
			}
		})
	}


	// 切换历史
	const switchHistory = (item) => {
		loadSessionMessages(item.id)
	}

	// 获取用户ID
	const getUserId = () => {
		try {
			let userInfo = uni.getStorageSync('userInfo')
			if (!userInfo) return null
			if (typeof userInfo === 'string') userInfo = JSON.parse(userInfo)
			return userInfo.data?.id || userInfo.id || null
		} catch (err) {
			return null
		}
	}

	// 发送消息
	const sendMsg = async () => {
		const content = inputContent.value.trim()
		if (!content || isLoading.value) return

		// 用户消息添加列表
		messages.value.push({
			role: 'user',
			content
		})
		inputContent.value = ''
		isLoading.value = true
		// AI加载动画
		const loadingIdx = messages.value.push({
			role: 'system',
			loading: true,
			content: ''
		}) - 1

		scrollToBottom()
		
		try {
			const res = await aiChat({
				session_id: currentSessionId.value,
				message: content
			})

			console.log('AI返回的内容:', res)

			if (res.data.code === 200 && res.data.data) {
				// 正常响应：展示 AI 回复内容
				const d = res.data.data
				const reply = d.ai_display_content || '暂未获取到回复，请重试'
				messages.value[loadingIdx] = {
					role: 'system',
					loading: false,
					content: reply,
				}
				// 行程类回复：先不落库，挂上待确认标记与计划数据，等用户点「添加到行程」
				if (d.response_type === 'itinerary' && d.needs_save) {
					Object.assign(messages.value[loadingIdx], {
						response_type: 'itinerary',
						needs_save: true,
						saved: false,
						itineraryData: d.data,
					})
				}
				// 保存会话 ID
				if (d.session_id) {
					currentSessionId.value = d.session_id
					isNewChat.value = false
				}
				// 刷新历史列表
				loadHistoryList()
			} else {
				// 后端业务错误（如 AI 服务调用失败、JSON 解析失败等）
				messages.value[loadingIdx] = {
					role: 'system',
					loading: false,
					content: res.data.message || 'AI 服务暂时不可用，请稍后重试'
				}
			}
			scrollToBottom()
		} catch (err) {
			messages.value[loadingIdx] = {
				role: 'system',
				loading: false,
				content: '请求超时或网络异常，请重试'
			}
		} finally {
			isLoading.value = false
			scrollToBottom()
		}
	}

	// 切换语音录制：第一次点击开始，再次点击停止并上传识别
	const toggleVoice = async () => {
		if (!voiceSupported.value || !voiceAvailable.value) {
			uni.showToast({
				title: voiceSupported.value ? '语音服务暂不可用' : '当前平台不支持语音输入',
				icon: 'none'
			})
			return
		}
		if (isLoading.value) return

		if (!isRecording.value) {
			try {
				await startVoiceRecord()
				isRecording.value = true
			} catch (err) {
				console.error('开始录音失败：', err)
				let msg = '无法开始录音'
				if (err && (err.name === 'NotAllowedError' || err.name === 'SecurityError')) {
					msg = '麦克风权限被拒绝，或需在本机(localhost)/HTTPS 下访问'
				} else if (err && err.message && err.message.indexOf('Web Audio') >= 0) {
					msg = '当前浏览器不支持语音录制'
				}
				uni.showToast({
					title: msg,
					icon: 'none'
				})
			}
		} else {
			isRecording.value = false
			uni.showLoading({
				title: '识别中...',
				mask: true
			})
			try {
				const rec = await stopVoiceRecord()
				if (!rec) {
					uni.hideLoading()
					return
				}
				const res = await uploadVoiceChat({
					blob: rec.type === 'blob' ? rec.blob : null,
					path: rec.type === 'path' ? rec.path : null,
					session_id: currentSessionId.value
				})
				handleVoiceResult(res)
			} catch (err) {
				console.error('语音上传失败：', err)
				const msg = (err && err.data && err.data.message) ||
					(err && err.errMsg) ||
					'语音识别失败，请重试'
				uni.showToast({
					title: msg,
					icon: 'none'
				})
			} finally {
				uni.hideLoading()
			}
		}
	}

	// 处理语音接口返回：展示识别文本(用户气泡) + AI 回复，并自动朗读(H5)
	const handleVoiceResult = (res) => {
		if (res && res.statusCode === 200 && res.data && res.data.code === 200) {
			const d = res.data.data || {}
			const recognized = d.recognized_text || ''
			// 用户气泡：识别出的语音文本
			messages.value.push({
				role: 'user',
				content: recognized || '（未识别到内容）'
			})
			// AI 加载占位
			const loadingIdx = messages.value.push({
				role: 'system',
				loading: true,
				content: ''
			}) - 1
			scrollToBottom()

			// 归一化 AI 回复内容（行程用 narrative，问答用 answer）
			let reply = ''
			if (d.response_type === 'itinerary') {
				reply = d.narrative || (d.data && d.data.narrative) || ''
			} else {
				reply = d.answer || (d.data && d.data.answer) || ''
			}
			if (!reply && d.narrative) reply = d.narrative
			if (!reply && d.answer) reply = d.answer
			reply = reply || '暂未获取到回复，请重试'

			messages.value[loadingIdx] = {
				role: 'system',
				loading: false,
				content: reply
			}
			// 行程类回复：挂上待确认标记与计划数据，等用户点「添加到行程」
			if (d.response_type === 'itinerary' && d.needs_save) {
				Object.assign(messages.value[loadingIdx], {
					response_type: 'itinerary',
					needs_save: true,
					saved: false,
					itineraryData: d.data,
				})
			}
			if (d.session_id) {
				currentSessionId.value = d.session_id
				isNewChat.value = false
			}
		loadHistoryList()
		scrollToBottom()
	} else {
			const msg = (res && res.data && res.data.message) || '语音识别失败，请重试'
			uni.showToast({
				title: msg,
				icon: 'none'
			})
		}
	}

	// 朗读/停止朗读 AI 回复（点击切换）：点一次朗读，再点一次停止
	const toggleSpeak = (idx, text) => {
		if (!isTTSAvailable()) {
			uni.showToast({
				title: '当前平台不支持语音朗读',
				icon: 'none'
			})
			return
		}
		// 正在朗读本条 → 停止朗读
		if (speakingIndex.value === idx) {
			stopSpeak()
			speakingIndex.value = null
			return
		}
		// 朗读新的一条（先停掉上一条，避免叠加）
		stopSpeak()
		speakText(text || '', {
			onEnd: () => {
				// 朗读自然结束，清除高亮
				if (speakingIndex.value === idx) speakingIndex.value = null
			}
		})
		speakingIndex.value = idx
	}

	// 确认将计划添加进行程（用户点「添加到行程」后调用，真正落库）
	const confirmSaveItinerary = async (item) => {
		if (!item || !item.itineraryData) return
		item.saving = true
		try {
			const res = await saveItinerary(item.itineraryData)
			if (res.data && res.data.code === 200) {
				item.saved = true
				item.tripId = (res.data.data && res.data.data.trip_id) || null
				uni.showToast({ title: '已添加到行程', icon: 'success' })
			} else {
				uni.showToast({
					title: (res.data && res.data.message) || '保存失败，请重试',
					icon: 'none'
				})
			}
		} catch (err) {
			console.error('保存行程失败：', err)
			uni.showToast({ title: '网络异常，保存失败', icon: 'none' })
		} finally {
			item.saving = false
		}
	}

	// 暂不添加：直接收起确认条，不落库
	const dismissSave = (item) => {
		if (!item) return
		item.needs_save = false
	}

	// 跳转到行程详情页
	const goTripDetail = (tripId) => {
		if (!tripId) return
		uni.navigateTo({ url: `/pages/trips/detail?trip_id=${tripId}` })
	}

	// 拿用户基础信息
	const get_UserInfo = async () => {
		try {
			const res = await getUserInfo()
			if (res.data.code === 200) {
				console.log('用户信息：', res.data.data)
				uni.setStorageSync('userInfo', res.data.data)
			}
		} catch (err) {
			console.log('获取用户信息失败：', err)
		}
	}

	// 优化滚动到底部函数（支持智能判断）
	const scrollToBottom = () => {
		if (messages.value.length === 0) return
		// 先清空再赋值，确保每次都能触发视图更新
		scrollIntoViewId.value = ''
		nextTick(() => {
			scrollIntoViewId.value = 'msg-' + (messages.value.length - 1)
		})
	}
</script>

<style scoped lang="scss">
	/* ===== 设计令牌 ===== */
	$brand: #2E86DE;
	$brand-dark: #1B6EC2;
	$brand-bg: #eef4fb;
	$text-1: #1e293b;
	$text-2: #64748b;
	$text-3: #94a3b8;
	$border: #e2e8f0;
	$bg-page: #f4f7fb;

	.chat-container {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 50px);
		background: $bg-page;
		font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', sans-serif;
	}

	/* 顶部状态栏：品牌渐变 */
	.status-bar {
		flex-shrink: 0;
		z-index: 10;
		padding: 14px 24rpx;
		padding-top: calc(14px + env(safe-area-inset-top));
		display: flex;
		justify-content: space-between;
		align-items: center;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		box-shadow: 0 8rpx 24rpx rgba(46, 134, 222, 0.18);
		border-bottom-left-radius: 24rpx;
		border-bottom-right-radius: 24rpx;
	}

	.location-name {
		font-size: 34rpx;
		font-weight: 600;
		color: #fff;
		letter-spacing: 1rpx;
	}

	.header-icons {
		display: flex;
		align-items: center;
		gap: 20rpx;
	}

	.icon-btn {
		font-size: 34rpx;
		color: white;
		background-color: rgba(255, 255, 255, 0.18);
		width: 64rpx;
		height: 64rpx;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.25s ease;
		backdrop-filter: blur(8px);
	}

	.icon-btn:active {
		background-color: rgba(255, 255, 255, 0.32);
		transform: scale(0.92);
	}

	/* 历史对话面板 */
	.history-panel {
		background: #fff;
		padding: 20rpx;
		max-height: 440rpx;
		overflow-y: auto;
		border-bottom: 1rpx solid $border;
		box-shadow: 0 8rpx 20rpx rgba(15, 23, 42, 0.06);
	}

	.history-item {
		padding: 22rpx 24rpx;
		border-radius: 14rpx;
		background: #f8fafc;
		margin-bottom: 14rpx;
		display: flex;
		justify-content: space-between;
		align-items: center;
		transition: all 0.2s ease;

		&:active {
			background: $brand-bg;
		}
	}

	.history-item .title {
		font-size: 28rpx;
		color: $text-1;
		font-weight: 500;
	}

	.history-item .time {
		font-size: 22rpx;
		color: $text-3;
	}

	.empty-history {
		text-align: center;
		padding: 40rpx;
		color: $text-3;
		font-size: 26rpx;
	}

	/* 对话列表 */
	.chat-list {
		flex: 1;
		padding: 28rpx 20rpx;
		overflow-y: auto;
	}

	.msg-item {
		display: flex;
		margin-bottom: 28rpx;
		align-items: flex-start;
	}

	.msg-item.ai {
		justify-content: flex-start;
	}

	.msg-item.user {
		justify-content: flex-end;
		margin-right: 8rpx;
	}

	.msg-content {
		max-width: 72%;
		padding: 24rpx 26rpx;
		border-radius: 24rpx;
		font-size: 28rpx;
		line-height: 1.6;
		box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.06);
		width: fit-content;
	}

	.ai .msg-content {
		background: #fff;
		color: $text-1;
		border-top-left-radius: 6rpx;
		min-width: 120rpx;
	}

	.user .msg-content {
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		color: #fff;
		border-top-right-radius: 6rpx;
		box-shadow: 0 8rpx 20rpx rgba(46, 134, 222, 0.25);
	}

	/* 加载动画 */
	.loading-container {
		display: flex;
		flex-direction: row;
		align-items: center;
		justify-content: center;
		gap: 10rpx;
		padding: 10rpx 0;
	}

	.loading-dot {
		width: 14rpx;
		height: 14rpx;
		border-radius: 50%;
		background: $brand;
		animation: loadingAnimation 1.4s ease-in-out infinite both;
	}

	.loading-dot:nth-child(1) {
		animation-delay: -0.32s;
	}

	.loading-dot:nth-child(2) {
		animation-delay: -0.16s;
	}

	.loading-dot:nth-child(3) {
		animation-delay: 0s;
	}

	.loading-dot:nth-child(4) {
		animation-delay: 0.16s;
	}

	.loading-dot:nth-child(5) {
		animation-delay: 0.32s;
	}

	@keyframes loadingAnimation {
		0% {
			transform: scale(0);
			opacity: 0.2;
		}

		50% {
			transform: scale(1);
			opacity: 1;
		}

		100% {
			transform: scale(0);
			opacity: 0.2;
		}
	}

	/* 输入框区域 */
	.input-box {
		display: flex;
		align-items: flex-end;
		background: #fff;
		border-radius: 36rpx;
		padding: 12rpx 16rpx;
		margin: 0 20rpx 20rpx;
		z-index: 999;
		box-shadow: 0 8rpx 24rpx rgba(15, 23, 42, 0.08);
		border: 1rpx solid $border;
	}

	.input {
		flex: 1;
		height: 120rpx;
		padding: 20rpx;
		font-size: 28rpx;
		border: none;
		outline: none;
		resize: none;
		background: transparent;
		color: $text-1;
	}

	.send-btn {
		min-width: 120rpx;
		height: 72rpx;
		background: linear-gradient(135deg, $brand 0%, #54A0FF 100%);
		color: #fff;
		border-radius: 36rpx;
		font-size: 28rpx;
		font-weight: 500;
		border: none;
		margin-bottom: 0;
		box-shadow: 0 6rpx 16rpx rgba(46, 134, 222, 0.3);
		transition: all 0.2s ease;

		&:active {
			transform: scale(0.96);
		}
	}

	.send-btn:disabled {
		background: #cbd5e1;
		box-shadow: none;
	}

	/* 麦克风按钮 */
	.mic-btn {
		flex-shrink: 0;
		width: 72rpx;
		height: 72rpx;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #eef4fb;
		border: 2rpx solid #cfe0f5;
		margin-right: 12rpx;
		transition: all 0.2s ease;
	}

	.mic-btn.recording {
		background: #ef4444;
		border-color: #ef4444;
		animation: micPulse 1.2s ease-in-out infinite;
	}

	.mic-btn-hover {
		opacity: 0.8;
	}

	@keyframes micPulse {

		0%,
		100% {
			transform: scale(1);
			box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5);
		}

		50% {
			transform: scale(1.08);
			box-shadow: 0 0 0 12rpx rgba(239, 68, 68, 0);
		}
	}

	/* 录音提示条 */
	.voice-hint {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12rpx;
		padding: 14rpx;
		margin: 0 20rpx 16rpx;
		font-size: 24rpx;
		color: #ef4444;
		background: #fef2f2;
		border-radius: 16rpx;
	}

	.voice-pulse {
		width: 18rpx;
		height: 18rpx;
		border-radius: 50%;
		background: #ef4444;
		animation: micPulse 1.2s ease-in-out infinite;
	}

	/* AI 消息体：文本 + 朗读按钮 */
	.msg-body {
		display: flex;
		align-items: flex-start;
		gap: 12rpx;
	}

	.msg-text {
		flex: 1;
		word-break: break-word;
	}

	.speak-btn {
		flex-shrink: 0;
		margin-top: 4rpx;
		padding: 6rpx;
		border-radius: 50%;
		background: #f1f5f9;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s ease;
	}

	.speak-btn-hover {
		background: #e2e8f0;
	}

	.speak-btn.active {
		background: #e0f0ff;
	}

	.history-left {
		flex: 1;
	}

	.del-btn {
		padding: 12rpx;
	}

	.del-btn:active {
		opacity: 0.6;
	}

	/* 行程待确认确认条 */
	.save-bar {
		width: 100%;
		box-sizing: border-box;
		margin-top: 20rpx;
		padding: 20rpx 22rpx;
		background: #f8fafc;
		border: 1rpx solid #e2e8f0;
		border-radius: 16rpx;
		display: flex;
		flex-direction: column;
		gap: 16rpx;
	}

	.save-bar-tip {
		font-size: 26rpx;
		color: #475569;
		line-height: 1.4;
	}

	.save-bar-actions {
		display: flex;
		gap: 18rpx;
		width: 100%;
	}

	.save-btn {
		flex: 1;
		font-size: 26rpx;
		line-height: 1.8;
		padding: 0;
		margin: 0;
		border-radius: 12rpx;
		border: none;
	}

	.save-btn::after {
		border: none;
	}

	.save-btn.primary {
		background: #2E86DE;
		color: #fff;
	}

	.save-btn.ghost {
		background: #fff;
		color: #64748b;
		border: 1rpx solid #cbd5e1;
	}

	.save-btn[disabled] {
		opacity: 0.6;
	}

	.save-done {
		width: 100%;
		box-sizing: border-box;
		margin-top: 18rpx;
		font-size: 26rpx;
		color: #16a34a;
	}

	.save-done-link {
		color: #2E86DE;
	}
</style>