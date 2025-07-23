from apscheduler.schedulers.background import BackgroundScheduler
from ingest_news import init_collection, fetch_articles_from_rss, embed_and_store_article
import logging

def scheduled_ingest():
    try:
        print("[Scheduler] Running news ingestion job...")
        init_collection()
        rss_url = "https://rss.app/feeds/z7n3qo1xCm03NWsq.xml"
        articles = fetch_articles_from_rss(rss_url)
        if articles:
            embed_and_store_article(articles)
            print("[Scheduler] Ingestion complete.")
        else:
            print("[Scheduler] No new articles to ingest.")
    except Exception as e:
        logging.exception(f"[Scheduler] Error during scheduled ingestion: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    
    # Change the hours=12 to whatever you want: 4, 6, etc.
    scheduler.add_job(scheduled_ingest, 'interval', hours=6)  

    scheduler.start()
    print("[Scheduler] Started background scheduler.")
    return scheduler
