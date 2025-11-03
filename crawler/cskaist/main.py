from crawler_ai import crawler_ai
from crawler_calendar import crawler_calendar
from crawler_lab import crawler_lab
from crawler_mem import crawler_mem
from crawler_news import crawler_news
from crawler_notice import crawler_notice
from crawler_profs import crawler_profs
from crawler_room import crawler_room
from csweb_save import purge

if __name__ == "__main__":
    print("Delete previous items...")
    purge()
    print("Done.")
    print("begin crawling...")
    crawler_ai()
    crawler_calendar()
    crawler_lab()
    crawler_mem()
    crawler_news()
    crawler_notice()
    crawler_profs()
    crawler_room()
    print("crawl complete.")