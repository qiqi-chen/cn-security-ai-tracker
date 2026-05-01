from typing import Dict, List
from models.news import RawNewsItem

CATEGORY_RULES: Dict[str, List[str]] = {
    "产品发布": ["发布", "上线", "推出", "发布会", "新产品", "新版本", "升级", "迭代", "更新", "正式发布"],
    "融资并购": ["融资", "并购", "收购", "投资", "战略合作", "IPO", "上市", "股权", "估值", "轮融资"],
    "技术突破": ["突破", "首创", "研发", "专利", "论文", "技术创新", "算法", "模型训练", "开源", "自研"],
    "安全事件": ["漏洞", "攻击", "勒索", "数据泄露", "入侵", "威胁", "CVE", "0day", "黑客", "勒索软件"],
    "政策法规": ["政策", "法规", "监管", "合规", "标准", "规范", "条例", "备案", "认证", "等保"],
    "市场动态": ["市场", "份额", "营收", "增长", "竞争", "排名", "报告", "分析", "行业", "趋势"],
}


class Classifier:
    def classify(self, item: RawNewsItem, cleaned_content: str) -> List[str]:
        text = f"{item.title} {cleaned_content}"
        matched = [cat for cat, kws in CATEGORY_RULES.items() if any(kw in text for kw in kws)]
        return matched if matched else ["其他"]
