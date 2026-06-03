"""
科目摘要数据加载模块。
启动时从 subject_summaries.json 缓存到内存，提供 get_subject_info() 查询。
JSON 文件只读，kid_app 不要写它。
LLM 生成使用 Gemini 2.5 Flash-Lite（最快、无 thinking）。
"""
import json
from pathlib import Path

_subjects_cache = None

def _load_subjects():
    global _subjects_cache
    if _subjects_cache is None:
        path = Path(__file__).parent.parent.parent / 'data' / 'subject_summaries.json'
        if not path.exists():
            _subjects_cache = {"subjects": []}
        else:
            with open(path, 'r', encoding='utf-8') as f:
                _subjects_cache = json.load(f)
    return _subjects_cache

def get_subject_info(item_name: str) -> dict | None:
    """根据科目名查找摘要。names 数组匹配 practice_items.name。"""
    data = _load_subjects()
    for s in data.get('subjects', []):
        if item_name in s.get('names', []):
            return s
    return None

def _get_google_key() -> str:
    """从 hermes .env 读取 Google API key。"""
    env_path = Path('/Users/mt16/.hermes/.env')
    if not env_path.exists():
        return ''
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith('GOOGLE_API_KEY=') and not line.startswith('#'):
            return line.split('=', 1)[1].strip()
    return ''

def _gemini_stream(prompt: str):
    """Gemini 2.5 Flash-Lite 流式生成。yield 每个 token。"""
    import requests as req
    api_key = _get_google_key()
    if not api_key:
        return

    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:streamGenerateContent?key={api_key}&alt=sse'

    try:
        resp = req.post(
            url,
            headers={'content-type': 'application/json'},
            json={
                'contents': [{'parts': [{'text': prompt}]}],
                'generationConfig': {
                    'maxOutputTokens': 200,
                    'temperature': 0.8,
                },
            },
            stream=True,
            timeout=10,
        )
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')
            if not line.startswith('data: '):
                continue
            data = line[6:]
            try:
                chunk = json.loads(data)
                candidates = chunk.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    for p in parts:
                        text = p.get('text', '')
                        if text:
                            yield text
            except json.JSONDecodeError:
                continue
    except Exception:
        pass

def generate_mood_stream(item_name: str):
    """流式生成练习心情。"""
    fallback = '练习加油'
    prompt = f'给8岁学竹笛的小朋友写一句关于「{item_name}」的练习心情，15字内，温暖鼓励，不要emoji不要引号。'
    result = []
    for token in _gemini_stream(prompt):
        result.append(token)
        yield token
    if not result:
        yield fallback

def generate_summary_stream(item_name: str):
    """流式生成小故事。"""
    info = get_subject_info(item_name)
    ctx = f'参考：{info.get("one_liner","")}' if info else ''
    prompt = f'给8岁小朋友讲一个关于「{item_name}」竹笛练习的有趣小故事，30-50字，活泼，不要emoji不要引号。{ctx}'
    result = []
    for token in _gemini_stream(prompt):
        result.append(token)
        yield token
    if not result:
        yield '暂无小故事'
