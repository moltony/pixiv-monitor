#!/usr/bin/env python3

import requests
import re
import illustlog
import argparse

# Copied from my browser, change this if you have trouble with CF bot check
USERAGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"

def get_user_id(stacc, phpsessid):
    response = requests.get(f"https://www.pixiv.net/stacc/{stacc}", cookies={
        "PHPSESSID": phpsessid
    }, headers={
        "User-Agent": USERAGENT
    })
    if not response.ok:
        return None
    text = response.text
    print(text)
    pattern = r'pixiv.context.userId = "(\d+)";'
    match = re.findall(pattern, text)[0]
    return int(match)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phpsessid", type=str, help="The PHPSESSID cookie for authentication.")
    args = parser.parse_args()

    illust_log = illustlog.get_illust_log()
    staccs = []
    for illust in illust_log["illusts"]:
        if illust["user"]["account"] not in staccs:
            staccs.append(illust["user"]["account"])
            print(f"Found user: {illust['user']['name']} (@{illust['user']['account']})")
    print(f"*** Found {len(staccs)} accounts")
    user_ids = []
    for stacc in staccs:
        user_id = get_user_id(stacc, args.phpsessid)
        if user_id is None:
            print(f"Account @{stacc} does not exist")
        else:
            print(f"@{stacc}: {user_id}")
            user_ids.append(user_id)

    print(f"User ID list:\n{user_ids}")

if __name__ == "__main__":
    main()
