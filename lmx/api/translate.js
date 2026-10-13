import request from '@/utils/request';

// 支持的语言代码映射
const LANG_MAP = {
	'中文': 'zh',
	'英语': 'en',
	'日语': 'jp',
	'韩语': 'kor',
	'法语': 'fra',
	'德语': 'de',
	'西班牙语': 'spa',
	'意大利语': 'it',
	'俄语': 'ru'
};

// 调用后端翻译代理（百度翻译签名在服务端计算，前端不再持有密钥）
export async function translateText(query, from, to) {
	if (!query || query.trim() === '') {
		return Promise.reject(new Error('翻译文本不能为空'));
	}

	try {
		const res = await request({
			url: '/api/proxy/translate',
			method: 'GET',
			data: {
				q: query,
				from_lang: 'auto',
				to_lang: to
			}
		});

		const text = res.data && res.data.data && res.data.data.text;
		if (text !== undefined && text !== null) {
			return text;
		}
		const msg = (res.data && res.data.message) || '翻译失败，未获取到结果';
		return Promise.reject(new Error(msg));
	} catch (error) {
		return Promise.reject(error);
	}
}

// 获取语言代码
export function getLanguageCode(languageName) {
	return LANG_MAP[languageName] || languageName;
}

// 获取语言名称
export function getLanguageName(code) {
	const languages = {
		'zh': '中文',
		'en': '英语',
		'jp': '日语',
		'kor': '韩语',
		'fra': '法语',
		'de': '德语',
		'spa': '西班牙语',
		'it': '意大利语',
		'ru': '俄语'
	};
	return languages[code] || code;
}
