"""
FraxVerse · 新闻采集器

从 AKShare（东方财富搜索API）获取A股财经新闻并存入 News 表。
支持去重（URL唯一键）、情感标记（预留）、增量采集。
"""

import logging
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import akshare as ak
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.db.session import get_session

logger = logging.getLogger(__name__)

# 采集关键词列表 — 覆盖A股主流财经资讯
COLLECT_KEYWORDS = [
    "财经要闻",
    "A股",
    "股市",
    "板块",
    "政策",
    "能源",
    "科技",
    "消费",
    "医药",
    "金融",
    "地产",
    "汽车",
    "新能源",
    "人工智能",
    "半导体",
]

# 来源映射：文章来源 → source / source_display
SOURCE_MAP: dict[str, tuple[str, str]] = {
    "财联社": ("cls", "财联社"),
    "华尔街见闻": ("wallstcn", "华尔街见闻"),
    "证券时报": ("stcn", "证券时报"),
    "证券时报网": ("stcn", "证券时报"),
    "上海证券报": ("sse", "上海证券报"),
    "中国证券报": ("cs", "中国证券报"),
    "第一财经": ("yicai", "第一财经"),
    "21世纪经济报道": ("21jingji", "21世纪经济报道"),
    "每日经济新闻": ("nbd", "每日经济新闻"),
    "界面新闻": ("jiemian", "界面新闻"),
    "财新": ("caixin", "财新"),
    "央广财经": ("cctv", "央广财经"),
    "经济观察报": ("eeo", "经济观察报"),
    "证券日报": ("zqrb", "证券日报"),
    "央视财经": ("cctv", "央视财经"),
    "人民日报": ("people", "人民日报"),
    "中国基金报": ("chinafund", "中国基金报"),
    "券商中国": ("券商中国", "券商中国"),
    "格隆汇": ("gelonghui", "格隆汇"),
    "e公司": ("ecompany", "e公司"),
    "数据宝": ("databao", "数据宝"),
    "新华网": ("xinhua", "新华网"),
    "中国证券网": ("cnstock", "中国证券网"),
    "时代周报": ("times", "时代周报"),
    "36氪": ("36kr", "36氪"),
    "国际金融报": ("ift", "国际金融报"),
    "华夏时报": ("chinatimes", "华夏时报"),
    "中国经营报": ("cb", "中国经营报"),
    "中国网财经": ("china", "中国网财经"),
    "央广网": ("cctv", "央广网"),
    "北京商报": ("bjnews", "北京商报"),
    "新京报": ("bjnews", "新京报"),
    "搜狐财经": ("sohu", "搜狐财经"),
    "新浪财经": ("sina", "新浪财经"),
    "新浪": ("sina", "新浪"),
}

# A股代码正则，用于从新闻内容中识别关联股票
# 北京时间 (UTC+8)
CST = timezone(timedelta(hours=8))

# A股代码正则，用于从新闻内容中识别关联股票
STOCK_CODE_RE = re.compile(r"([SHBZ]{2}\d{6})|(\d{6})")


def _classify_source(media_name: str) -> tuple[str, str, str]:
    """根据文章来源分类，返回 (source_id, display_name, category)"""
    media_name = media_name.strip()
    if media_name in SOURCE_MAP:
        sid, display = SOURCE_MAP[media_name]
        return sid, display, "finance"
    # 未匹配到映射，fallback
    return "other", media_name, "finance"


def _extract_related_stocks(title: str, content: str) -> list[str]:
    """从标题和内容中提取关联的A股代码"""
    stocks: set[str] = set()
    text_all = f"{title} {content}" if content else title
    for match in STOCK_CODE_RE.finditer(text_all):
        code = match.group(1) or match.group(2)
        # 简单过滤：6位数字
        if len(code) == 6:
            stocks.add(code)
    return sorted(stocks)


def _dedup_news(news_list: list[dict[str, Any]], db: Session) -> list[dict[str, Any]]:
    """批量去重：查询已存在的URL，只返回新记录"""
    urls = [n["url"] for n in news_list if n.get("url")]
    if not urls:
        return []

    # 分批查询避免SQL过长
    existing_urls: set[str] = set()
    batch_size = 200
    for i in range(0, len(urls), batch_size):
        batch = urls[i : i + batch_size]
        placeholders = ", ".join(f"'{u.replace(chr(39), chr(39)+chr(39))}'" for u in batch)
        rows = db.execute(
            text(f"SELECT url FROM news WHERE url IN ({placeholders})")
        ).fetchall()
        for row in rows:
            existing_urls.add(row[0])

    return [n for n in news_list if n.get("url") not in existing_urls]


def collect_hot_news(
    keywords: list[str] | None = None, db: Session | None = None
) -> int:
    """
    采集热点新闻主入口。

    循环 keywords 调用 AKShare stock_news_em()，去重后写入 news 表。

    Returns:
        本次新增的新闻条数
    """
    keywords = keywords or COLLECT_KEYWORDS
    close_db = db is None
    if close_db:
        db = get_session()

    try:
        all_news: list[dict[str, Any]] = []
        for keyword in keywords:
            try:
                logger.info(f"[news] 采集关键词: {keyword}")
                df: pd.DataFrame = ak.stock_news_em(symbol=keyword)
                if df is None or df.empty:
                    logger.warning(f"[news] {keyword} 返回空数据")
                    continue

                for _, row in df.iterrows():
                    title = str(row.get("新闻标题", "")).strip()
                    content = str(row.get("新闻内容", "")).strip()
                    media_name = str(row.get("文章来源", "")).strip()
                    pub_time_str = str(row.get("发布时间", "")).strip()
                    url = str(row.get("新闻链接", "")).strip()

                    if not title or not url:
                        continue

                    # 解析时间 — AKShare返回北京时间（如 "2026-05-02 06:30:41"）
                    try:
                        naive = datetime.strptime(pub_time_str, "%Y-%m-%d %H:%M:%S")
                        pub_time = naive.replace(tzinfo=CST)  # 标记为 UTC+8
                    except (ValueError, TypeError):
                        pub_time = datetime.now(timezone.utc)

                    source_id, source_display, category = _classify_source(media_name)
                    related_stocks = _extract_related_stocks(title, content)

                    all_news.append(
                        {
                            "source": source_id,
                            "source_display": source_display,
                            "category": category,
                            "title": title,
                            "content": content,
                            "url": url,
                            "published_at": pub_time,
                            "related_stocks": related_stocks,
                            "is_hot": True,
                            "hot_score": 0,
                        }
                    )
            except Exception as e:
                logger.error(f"[news] 关键词 {keyword} 采集失败: {e}")
                continue

        if not all_news:
            logger.info("[news] 本次采集无数据")
            return 0

        # 去重
        new_news = _dedup_news(all_news, db)
        if not new_news:
            logger.info("[news] 去重后无新数据")
            return 0

        # 批量插入
        inserted = 0
        for item in new_news:
            try:
                related_stocks_json = json.dumps(item.get("related_stocks", []))
                db.execute(
                    text(
                        """
                        INSERT INTO news (source, source_display, category, title,
                            content, url, published_at, related_stocks, is_hot, hot_score)
                        VALUES (:source, :source_display, :category, :title,
                            :content, :url, :published_at, CAST(:related_stocks AS jsonb), :is_hot, :hot_score)
                        ON CONFLICT (url) DO NOTHING
                        """
                    ),
                    {
                        "source": item["source"],
                        "source_display": item["source_display"],
                        "category": item["category"],
                        "title": item["title"],
                        "content": item.get("content", ""),
                        "url": item["url"],
                        "published_at": item["published_at"],
                        "related_stocks": related_stocks_json,
                        "is_hot": item.get("is_hot", True),
                        "hot_score": item.get("hot_score", 0),
                    },
                )
                inserted += 1
            except Exception as e:
                logger.warning(f"[news] 插入失败: {e}")
                continue

        db.commit()
        logger.info(f"[news] 采集完成: 总计 {len(all_news)} 条, 新增 {inserted} 条")
        return inserted

    except Exception as e:
        db.rollback()
        logger.error(f"[news] 采集异常: {e}", exc_info=True)
        return 0
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    count = collect_hot_news()
    print(f"\n✅ 采集完成，新增 {count} 条新闻")
