import os
import re
import bs4
import urllib.request
import urllib.error
import time
import uuid
import json
import lib

SITE_URL = "https://www.steamcardexchange.net"
ALL_GAME_LIST_URL = SITE_URL + "/index.php?badgeprices"
APP_INFO_URL = SITE_URL + "/index.php?gamepage-appid-{appid}"


def download_file(url, dst_path):
    try:
        with urllib.request.urlopen(url) as web_file:
            data = web_file.read()
            with open(dst_path, mode='wb') as local_file:
                local_file.write(data)
    except urllib.error.URLError as e:
        print(e)
	
def download_file_to_dir(url, dst_dir):
    download_file(url, os.path.join(dst_dir, os.path.basename(url)))

	

with open("all_url_tbody.txt", "r", encoding="utf-8") as f:
	tbody_text = f.read()
	appid_list = re.findall(r'gamepage-appid-(\d+)"', tbody_text)

for i, appid in enumerate(appid_list):
	try:
		response = urllib.request.urlopen(APP_INFO_URL.format(appid=appid))
		soup = bs4.BeautifulSoup(response, features="html.parser")
		soup_img_list = soup.find("div", class_="showcase-element-container badge").find_all("img")
		dir_name = soup.head.title.text.replace("Showcase :: ", "")
		json_data = {
			"title": dir_name,
			"appid": int(appid),
			"img_num": len(soup_img_list),
		}
		dir_name = "images/" + dir_name
		lib.print_log(f"{i}/{len(appid_list)} {dir_name}")
		try:
			os.makedirs(dir_name, exist_ok=True)
		except Exception:
			dir_name = "images/" + str(uuid.uuid1())
			os.makedirs(dir_name, exist_ok=True)
		for j, row in enumerate(soup_img_list):
			download_file(row["src"], dir_name + f"/level{j + 1}.png")
			lib.print_log(row["src"])

		with open(dir_name + "/data.json", "w", encoding="utf-8") as f:
			f.write(json.dumps(json_data, ensure_ascii=False, indent=4))
	except Exception as e:
		lib.print_error_log(f"{i}/{len(appid_list)} {dir_name}")
		lib.print_error_log(e)
	time.sleep(5)