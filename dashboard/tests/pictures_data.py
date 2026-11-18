"""Real-shaped data of the Pictures card: a cut-down artifact of GTV's picture ticket of 2026-10-24 (image_links_export), OnBuy's own listing records for the SKUs the sheet had no OPC for
(listing_lookup) and the logs of repair_shifted_content (the dry runs and the canary of YRA, 2026-10-09 / 10-22)."""
import io
import zipfile

MAIN = {"734381598114": "https://m.media-amazon.com/images/I/71AnHBlD6WL.jpg", "734375635184": "https://m.media-amazon.com/images/I/81kri8+3LpL.jpg",
        "734375050444": "https://m.media-amazon.com/images/I/71hHCFcLKOL.jpg", "735719813442": "https://m.media-amazon.com/images/I/61dRu3gw0QL.jpg",
        "735739982043": "https://m.media-amazon.com/images/I/61dRu3gw0QL.jpg"}
EXTRA = {"734381598114": "https://m.media-amazon.com/images/I/81XTPltoGmL.jpg,https://m.media-amazon.com/images/I/71IpTPT-LLL.jpg,https://m.media-amazon.com/images/I/61CAPCcXY9L.jpg",
         "734375635184": "https://m.media-amazon.com/images/I/81XTPltoGmL.jpg,https://m.media-amazon.com/images/I/71eEpr4KwPL.jpg",
         "734375050444": "https://m.media-amazon.com/images/I/71LTbhzTFzL.jpg,https://m.media-amazon.com/images/I/914RemP5ucL.jpg",
         "735719813442": "https://m.media-amazon.com/images/I/61ICCMWUH0L.jpg,https://m.media-amazon.com/images/I/71VM6pvZVfL.jpg",
         "735739982043": "https://m.media-amazon.com/images/I/61YK8lgvZhL.jpg,https://m.media-amazon.com/images/I/71rRfv2uqYL.jpg"}
STATUS = "Awaiting OnBuy go-live (created earlier - listing not yet updatable)"

ALL_FOUND = ("﻿SKU,Tab,Row,OPC,Sync Status,Main image link,Additional image links\n"
             f"734381598114,Amazon,4911,PYQX8PS,{STATUS},{MAIN['734381598114']},\"{EXTRA['734381598114']}\"\n"
             f"734375635184,Amazon,4910,PYQX8PR,{STATUS},{MAIN['734375635184']},\"{EXTRA['734375635184']}\"\n"
             f"734375050444,Amazon,4909,PYQX8PQ,{STATUS},{MAIN['734375050444']},\"{EXTRA['734375050444']}\"\n"
             f"735719813442,Amazon,4992,,Synced,{MAIN['735719813442']},\"{EXTRA['735719813442']}\"\n"
             f"735739982043,Amazon,4993,,Synced,{MAIN['735739982043']},\"{EXTRA['735739982043']}\"\n")
REFERENCE = ("﻿SKU,Tab,Row,OPC,Sync Status,OnBuy Product Created,Product URL,Title\n"
             f"734381598114,Amazon,4911,PYQX8PS,{STATUS},TRUE,https://onbuy.com/gb/p/hisense-dh1q802bw2~p293329003/,\"Hisense DH1Q802BW2 60cm Freestanding 8 KG Heatpump Front Load Tumble Dryer\"\n"
             f"734375635184,Amazon,4910,PYQX8PR,{STATUS},TRUE,https://onbuy.com/gb/p/hisense-3s-wifi-series-dh3s802bw3~p293329004/,\"Hisense 3S WiFi Series DH3S802BW3 60cm Freestanding\"\n"
             f"734375050444,Amazon,4909,PYQX8PQ,{STATUS},TRUE,https://onbuy.com/gb/p/hisense-5-series-dh5s102bw~p293329005/,\"Hisense 5 Series DH5S102BW 60cm Freestanding\"\n"
             "735719813442,Amazon,4992,,Synced,,,\"HP LaserJet Pro MFP 3302sdw Laser Printer\"\n"
             "735739982043,Amazon,4993,,Synced,,,\"HP LaserJet Pro MFP 3302fdw Laser Printer\"\n")
NO_OPC = ("﻿SKU,Tab,Row,OPC,Sync Status,Title\n735719813442,Amazon,4992,,Synced,\"HP LaserJet Pro MFP 3302sdw Laser Printer\"\n"
          "735739982043,Amazon,4993,,Synced,\"HP LaserJet Pro MFP 3302fdw Laser Printer\"\n")
TICKET = ("﻿OPC,SKU,Main image link,Additional image links\n")
DUPLICATES = "﻿SKU,Found at\n734375050444,Amazon row 4909,Sheet1 row 12\n"
NOT_ON_SHEET = "999000111\n"

EXPORT_FILES = {"all_found_images.csv": ALL_FOUND, "reference.csv": REFERENCE, "no_opc.csv": NO_OPC, "ticket_image_links.csv": TICKET, "duplicates.csv": DUPLICATES,
                "not_on_sheet.txt": NOT_ON_SHEET}

# OnBuy's own records (listing_lookup.yml: LISTING|<json>, the sweep's misses as NOT IN SWEEP)
LOOKUP_LOG = """swept 8883 listings; matched 3 of 4 requested SKUs
LISTING|{"name": "HP LaserJet Pro MFP 3302sdw Laser Printer | Colour, Printer for Small Medium Business | Print, Scan, Copy | Automatic document feeder | 2-Sided", "sku": "735719813442", "price": "417.03", "stock": 5, "delivery_template_id": 56859, "opc": "PYQX8T7", "product_url": "https://www.onbuy.com/gb/p/hp-laserjet-pro-mfp-3302sdw~p293329091", "image_url": "https://onbuy.com/files/default/product/thumb/default.jpg", "created_at": "2026-10-23 01:44:14", "updated_at": "2026-10-24 00:49:58"}
LISTING|{"name": "HP LaserJet Pro MFP 3302fdw Laser Printer | Colour | Printer for Small Medium Business | Print, Scan, Copy, Fax | Automatic document feeder | 2-Sided", "sku": "735739982043", "price": "505.61", "stock": 5, "delivery_template_id": 56859, "opc": "PYQX8T8", "product_url": "https://www.onbuy.com/gb/p/hp-laserjet-pro-mfp-3302fdw~p293329092", "image_url": "https://onbuy.com/files/default/product/thumb/default.jpg", "created_at": "2026-10-23 01:44:17", "updated_at": "2026-10-24 00:49:58"}
LISTING|{"name": "Hisense DH1Q802BW2 60cm Freestanding 8 KG Heatpump Front Load Tumble Dryer", "sku": "734381598114", "price": "0.00", "stock": 0, "delivery_template_id": 56859, "opc": "PYQX8PS", "product_url": "https://www.onbuy.com/gb/p/hisense-dh1q802bw2~p293329003", "image_url": "https://onbuy.com/files/default/product/thumb/default.jpg", "created_at": "2026-10-22 01:39:45", "updated_at": "2026-10-23 01:40:47"}
NOT IN SWEEP: 999000111
"""

# YRA's dry run of 2026-10-22 13:03Z (cut to four targets) and its canary of 2026-10-09 (three submitted OK)
REPAIR_DRY_LOG = """
worksheet: Amazon
INFO live listings: 8079
INFO shift-repairable: 4 (skipped incomplete: 1) | barcode-collision (report-only): 1
INFO   COLLISION row 1288 SKU 668580542916 | onbuy: Warrior Motorcycle Rear Paddock Stand | sheet: 1000W Omelette Maker
INFO   target 667770448984 (onbuy shows: Avio Carry-On Cabin Luggage 55x40x20cm | Hard Shell Suitcase)
INFO   target 668159164105 (onbuy shows: Bearwind Electric Hand Warmers Rechargeable, 2 Pack Magnetic)
INFO   target 668196396682 (onbuy shows: Garmin HRM-600, Premium Heart Rate Monitor, HRV data,Running)
INFO   target 669347170304 (onbuy shows: Anycubic Kobra 3 Max V2 FDM 3D Printer, 420420500mm³ Large P)
INFO DRY RUN - nothing submitted
"""
REPAIR_LIVE_LOG = """
INFO live listings: 6258
INFO shift-repairable: 3 (skipped incomplete: 0) | barcode-collision (report-only): 0
INFO REPAIR_LIMIT: repairing first 3
INFO   target 328989649226 (onbuy shows: Acer A640 4K Webcam for PC with Sony Sensor PDAF Autofocus A)
INFO   target 329020985778 (onbuy shows: Kodak PIXPRO FZ55 1/2.3" Compact camera 16 MP CMOS 4608 x 34)
INFO   target 329026989923 (onbuy shows: TeQsli 25cm Double Mattress Medium Firm 7-Zone Support Hybri)
INFO REPAIR 328989649226: submitted OK
INFO REPAIR 329020985778: submitted OK
INFO REPAIR 329026989923: submitted OK
INFO DONE: 3 submitted, 0 failed (content applies after OnBuy's queue processes)
worksheet: Amazon
"""
REPAIR_MIXED_LOG = """
INFO live listings: 6258
INFO shift-repairable: 3 (skipped incomplete: 0) | barcode-collision (report-only): 0
INFO   target 328989649226 (onbuy shows: Acer A640 4K Webcam)
INFO   target 329020985778 (onbuy shows: Kodak PIXPRO FZ55)
INFO   target 329026989923 (onbuy shows: TeQsli Mattress)
INFO REPAIR 328989649226: submitted OK
WARNING REPAIR 329020985778: failed - HTTP 400 {"errors": ["image not reachable"]}
WARNING rate limited (429) - stopping this run; re-dispatch to continue
INFO DONE: 1 submitted, 1 failed (content applies after OnBuy's queue processes)
"""


def make_zip(files):
    """An artifact's zip as GitHub serves it (the files at the root)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(name, text.encode("utf-8"))
    return buf.getvalue()


def fake_fetch(dead=(), errors=()):
    """A link opener for tests: every link answers 200 image/jpeg except the `dead` ones (404) and the `errors` ones (no answer)."""
    def fetch(url):
        if url in dead:
            return 404, "text/html"
        if url in errors:
            return 0, "timed out"
        return 200, "image/jpeg"
    return fetch


class Links:
    """The link opener of the app in the tests: every link answers 200 image/jpeg except the `dead` ones (404) and the `errors` ones (no answer). `opened` = every link it was asked for."""

    def __init__(self):
        self.dead, self.errors, self.opened = set(), set(), []

    def __call__(self, url):
        self.opened.append(url)
        if url in self.dead:
            return 404, "text/html"
        if url in self.errors:
            return 0, "timed out"
        return 200, "image/jpeg"
