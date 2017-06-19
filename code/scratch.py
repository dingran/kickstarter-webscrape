# -*- coding: utf-8 -*-
"""
Created on Thu Oct 13 10:06:12 2016

@author: ran
"""

from bs4 import BeautifulSoup
import urllib2
import pandas as pd
import pandas as np
import os
import json
import datetime
import iso8601
import re
import unicodedata
import sys
import pandas as pd

working_dir = '/Users/ran/Dropbox/kickstarter_webscrape'
output_dir = os.path.join(working_dir, 'output')
page_store_folder = os.path.join(output_dir, 'index_pages')
past_proj_page_store_folder = os.path.join(output_dir, 'past_project_pages')

parser = 'lxml'
domain = 'https://www.kickstarter.com/'
file_list = []
output_fname_template = os.path.join(output_dir, 'proj_list_tech_top{}pages_{}.csv')

target_link_template = 'https://www.kickstarter.com/discover/advanced?category_id=16&woe_id=0&sort=magic&seed=2460612&page={}'

N_pages = 200
overwrite = False

# %%
for p in range(N_pages):
    target_link = target_link_template.format(p)
    page_filename = os.path.join(page_store_folder, 'page_{}.html'.format(p))

    if not overwrite and os.path.exists(page_filename):
        print target_link, 'exists, skipping...'

    else:
        print target_link, 'processing...'

        u = target_link
        try:
            page = urllib2.urlopen(u).read()
        except:
            print 'failed to open page'
            continue

        with open(page_filename, 'w') as p:
            p.write(page)

    file_list.append(page_filename)

# %%

projs = []
counter = 0
for u in file_list:
    counter += 1
    print '{}/{}'.format(counter, len(file_list))
    with open(u, 'r') as f:
        page = f.read()
    soup = BeautifulSoup(page, parser)

    cards = soup(class_='project-card')
    n_card = len(cards)

    for i in range(n_card):
        # print u, i
        info = dict()
        b = cards[i]

        title_obj = b(class_='project-card-content')[0](class_='project-title')
        if title_obj:
            headline = title_obj[0].get_text()
            info['active'] = 1
            info['byline'] = b(class_='project-card-content')[0](class_='project-byline')[0].get_text().strip()
            info['description'] = b(class_='project-card-content')[0](class_='project-blurb')[0].get_text().strip()
            # info['id'] = b(class_='project-card-content')[0]('a')[0]['data-pid']
            loc_dict = json.loads(
                b(class_='project-card-footer')[0](class_='project-location')[0]('a')[0]['data-location'])

            info['city'] = loc_dict['name']

            info['state'] = loc_dict['state']

            funded_pct = \
                b(class_='project-card-footer')[0](class_='project-stats-container')[0](class_="project-stats")[0](
                    'li')[0](
                    class_='project-stats-value')[0].get_text()

            info['funded_pct'] = funded_pct

            m = \
                b(class_='project-card-footer')[0](class_='project-stats-container')[0](class_="project-stats")[0](
                    'li')[1](
                    class_='money')[0].get_text()
            mm = m.replace(',', '')

            parse_money = re.compile(r'([\D]+)([\d]+)')
            funded_amt = parse_money.search(mm).group(2)
            currency = parse_money.search(mm).group(1)

            info['currency'] = currency
            info['funded_amt'] = funded_amt

            tt = \
                b(class_='project-card-footer')[0](class_='project-stats-container')[0](class_="project-stats")[0]('li',
                                                                                                                   class_='ksr_page_timer')[
                    0]['data-end_time']

            end_date = iso8601.parse_date(tt).date()

            info['end_date'] = end_date
        else:
            headline = b(class_='project-card-content')[0](class_='project-profile-title')[0].get_text().strip()
            info['active'] = 0
            info['byline'] = None
            info['description'] = b(class_='project-card-content')[0](class_='project-profile-blurb')[
                0].get_text().strip()

        info['headline'] = headline
        # h = unicodedata.normalize('NFKD', headline).encode('ascii', 'replace')
        try:
            parse_title = re.compile(r'((.*)[-:,])')
            title = parse_title.search(headline).group(1)
            info['title'] = title

        except:
            # print headline
            words = headline.split()
            if len(words) <= 3:
                info['title'] = headline
            else:
                info['title'] = words[0]

                # print info['title']

        rel_url = b(class_='project-card-content')[0]('a')[0]['href']
        info['url'] = urllib2.urlparse.urljoin(domain, rel_url)

        projs.append(info)

# %%

partial_output_fname = output_fname_template.format(N_pages, 'partial')
proj_df = pd.DataFrame(projs)
proj_df = proj_df.drop_duplicates()
proj_df.to_csv(partial_output_fname, index=False, encoding='utf-8')

# %%

df = pd.read_csv(partial_output_fname)

df_active = df[df['active'] == 1].copy()
df_past = df[df['active'] == 0].copy()

# %%
from progressbar import Bar, ETA, Percentage, ProgressBar, RotatingMarker, Timer

counter = 0

past_proj_page_fname_template = os.path.join(past_proj_page_store_folder, 'past_{}.html')

N = len(df_past)
widgets = ['download past projects', ': ', Percentage(), ' ', Bar(), ' ', ETA()]
pbar = ProgressBar(widgets=widgets, maxval=N).start()
overwrite = False
for index, row in df_past.iterrows():
    # print row['url']
    counter += 1
    print '{}/{}'.format(counter, N)
    # pbar.update(counter)
    fname = past_proj_page_fname_template.format(index)
    if (not overwrite) and os.path.exists(fname):
        print 'file exists, do not overwrite enabled, skipping'
    else:
        u = row['url'].replace('?ref=category', '/description')
        try:
            page = urllib2.urlopen(u).read()
        except:
            print 'failed to open page', u
            continue

        with open(fname, 'w') as p:
            p.write(page)

    with open(fname, 'r') as f:
        page = f.read()
    soup = BeautifulSoup(page, parser)

    try:
        location = soup(class_='NS_projects__category_location')[0]('a')[0].get_text().strip().split(', ')
        df_past.loc[index, 'city'] = location[0]
        df_past.loc[index, 'state'] = location[1]
    except:
        pass

    fund = soup(class_='NS_projects__category_location')[0].parent.parent.find_next_siblings('div')[0].get_text()

    parse_fund = re.compile(r'([\d,]+)')

    fund_list = parse_fund.findall(fund)

    df_past.loc[index, 'funded_amt'] = float(fund_list[0].replace(',', ''))

    df_past.loc[index, 'funded_pct'] = df_past.loc[index, 'funded_amt'] * 100 / float(fund_list[1].replace(',', ''))

# pbar.finish()
# %%
final_output_fname = output_fname_template.format(N_pages, 'full')
df_full = pd.concat([df_active, df_past])
df_full.to_csv(final_output_fname, index=False, encoding='utf-8')
