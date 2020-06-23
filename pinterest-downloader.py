# -*- coding: utf-8 -*-
# The MIT License (MIT)
# Copyright (c) 2020 limkokhole@gmail.com
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the 'Software'), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

__author__ = 'Lim Kok Hole'
__copyright__ = 'Copyright 2020'
__credits__ = ['Inspired by https://github.com/SevenLines/pinterest-board-downloader', 'S/O']
__license__ = 'MIT'
# Version increase if the output file/dir naming incompatible with existing
#, which might re-download for some files of previous version because of dir/filename not match
__version__ = 1.4
__maintainer__ = 'Lim Kok Hole'
__email__ = 'limkokhole@gmail.com'
__status__ = 'Production'

# Note: Support python 3 but not python 2

import sys, os, traceback
import platform
plat = platform.system().lower()
if ('window' in plat) or plat.startswith('win'):
    # Darwin should treat as Linux
    IS_WIN = True
else:
    IS_WIN = False
try:
    import readline #to make input() edit-able by LEFT key
except ModuleNotFoundError:
    pass

try:
    x_tag = '✖'
    done_tag = '✔'
    plus_tag = '➕'
    pinterest_logo = '🅿️'
    # Test Windows unicode capability by printing logo, throws if not:
    print(pinterest_logo, end='\r')
    sys.stdout.flush()
except UnicodeEncodeError:
    x_tag = 'x'
    done_tag = 'DONE'
    plus_tag = '+'
    pinterest_logo = 'P'
    
import argparse
import time
from datetime import datetime, timedelta

import json
import lxml.html as html

import urllib
import requests

from termcolor import cprint
import colorama
from colorama import Fore
colorama.init() # Windows need this

#ANSI_CLEAR = '\x1b[0m\x1b[K'
HIGHER_GREEN = Fore.LIGHTGREEN_EX
HIGHER_RED = Fore.LIGHTRED_EX
BOLD_ONLY = ['bold']

from concurrent.futures import ThreadPoolExecutor, as_completed

# RIP UA, https://groups.google.com/a/chromium.org/forum/m/#!msg/blink-dev/-2JIRNMWJ7s/yHe4tQNLCgAJ
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.0.0 Safari/537.36'

def quit(msgs, exit=True):
    if not isinstance(msgs, list):
        msgs = [msgs]
    if exit:
        msgs[-1]+= ' Abort.'
    for msg in msgs:
        if msg == '\n':
            print('\n')
        else:
            cprint(''.join([ HIGHER_RED, '%s' % (msg) ]), end='\n' )


# https://stackoverflow.com/a/34325723/1074998
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='#'):
    '''
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    '''
    if total != 0: # ZeroDivisionError: float division by zero
        percent = ('{0:.' + str(decimals) + 'f}').format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        #sys.stdout.write('\r{} |{}| {}%% {}'.format(prefix, bar, percent, suffix))
        cprint(''.join([ HIGHER_GREEN, '%s' % ('\r{} |{}| {}% {}'.format(prefix, bar, percent, suffix)) ]), attrs=BOLD_ONLY, end='' )
        sys.stdout.flush()


#imgs:
#source_url=%2Fmistafisha%2Fanimals%2F&data=%7B%22options%22%3A%7B%22isPrefetch%22%3Afalse%2C%22board_id%22%3A
#%2253761857990790784%22%2C%22board_url%22%3A%22%2Fmistafisha%2Fanimals%2F%22%2C%22field_set_key%22%3A%22react_grid_pin
#%22%2C%22filter_section_pins%22%3Atrue%2C%22sort%22%3A%22default%22%2C%22layout%22%3A%22default%22%2C%22page_size
#%22%3A25%2C%22redux_normalize_feed%22%3Atrue%7D%2C%22context%22%3A%7B%7D%7D&_=1592340515565
# unquote:
#'source_url=/mistafisha/animals/&data={"options":{"isPrefetch":false,"board_id":"53761857990790784"
#,"board_url":"/mistafisha/animals/","field_set_key":"react_grid_pin","filter_section_pins":true,"sort":"default"
#,"layout":"default","page_size":25,"redux_normalize_feed":true},"context":{}}&_=1592340515565
VER = (None, 'c643827', 'b0e3c4c')
def get_session(ver_i):
    s = requests.Session()
    if ver_i == 0:
        s.headers = {
            #'Host': 'www.pinterest.com',
            'User-Agent': UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive'
        }
    elif ver_i == 3:
        s.headers = {
            #'Host': 'www.pinterest.com', #Image can be https://i.pinimg.com, so let it auto or else fail
            'User-Agent': UA,
            'Accept': 'image/webp,*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.pinterest.com/',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'TE': 'Trailers'
        }

    elif ver_i == 4:
        # 'https://v.pinimg.com/videos/mc/hls/8a/99/7d/8a997df97cab576795be2a4490457ea3.m3u8' 
        s.headers = {
            'User-Agent': UA,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Origin': 'https://www.pinterest.com',
            'DNT': '1',
            'Referer': 'https://www.pinterest.com/',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

    else: # == 1, 2
        s.headers = {
            #'Host': 'www.pinterest.com',
            'User-Agent': UA,
            'Accept': 'application/json, text/javascript, */*, q=0.01',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.pinterest.com/',
            'X-Requested-With': 'XMLHttpRequest',
            'X-APP-VERSION': VER[ver_i],
            'X-Pinterest-AppState': 'active',
            'X-Requested-With': 'XMLHttpRequest',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'TE': 'Trailers'
        }

    return s


'''
def get_user_boards(username):
    s = get_session(0)
    r = s.get('https://www.pinterest.com/{}/'.format(username), timeout=30)
    root = html.fromstring(r.content)
    tag = root.xpath("//script[@id='initial-state']")[0]
    initial_data = json.loads(tag.text)
    
    boards = [i for i in initial_data['resourceResponses'] if i['name'] == 'UserProfileBoardResource']

    if boards:
        boards = boards[0]['response']['data'][0]

    return boards
'''


def get_pin_info(pin_id, arg_timestamp_log, arg_force_update, arg_dir, arg_cut, fs_f_max):
    s = get_session(0)

    r = s.get('https://www.pinterest.com/pin/{}/'.format(pin_id), timeout=30)
    root = html.fromstring(r.content)
    #print(root)
    tag = root.xpath("//script[@id='initial-state']")[0]
    initial_data = json.loads(tag.text)
    #print(initial_data)
    images = initial_data['resourceResponses'][0]['response']['data']
    #print(images.keys())
    try:
        # This is the User Responsibilities to ensure -d is not too long
        # Program can't automate for you, imagine -d already 2045th bytes in full path
        #, is unwise if program make dir in parent directory.
        create_dir(arg_dir)
        write_log( arg_timestamp_log, arg_dir, [images], images['id'] )
        IMG_SESSION = get_session(3)
        V_SESSION = get_session(4)
        print('[i] Download Pin id: ' + str(images['id']) + ' in directory: ' + arg_dir)
        printProgressBar(0, 1, prefix='[...] Downloading:', suffix='Complete', length=50)
        download_img(images, arg_dir, arg_force_update, IMG_SESSION, V_SESSION, arg_cut,  fs_f_max)
        printProgressBar(1, 1, prefix='[' + done_tag + '] Downloaded:', suffix='Complete   ', length=50)
    except KeyError:
        return quit(traceback.format_exc())
    print()


def get_board_info(board_name, exclude_section, section):
    s = get_session(0)

    r = s.get('https://www.pinterest.com/{}/'.format(board_name), timeout=30)
    root = html.fromstring(r.content)
    tag = root.xpath("//script[@id='initial-state']")[0]
    initial_data = json.loads(tag.text)
    if section:
        #print(len(initial_data['resourceResponses']))
        #3 index: BoardResource(0) -> BoardFeedResource -> BoardSectionsResource (2)
        boards = {}
        # 3 keys: 'rebuildStoreOnClient', 'resourceResponses', 'routeData'
        #print(initial_data['resourceResponses']) 
        for i in initial_data['resourceResponses']:
            if i['name'] == 'BoardFeedResource':
                for boa in i['response']['data']:
                    boards['board'] = boa['board']
                    break # only nid once bcoz the rest is repeat
            elif i['name'] == 'BoardSectionsResource':
                for sec in i['response']['data']:
                    if sec['slug'] == section:
                        #print(sec)
                        boards['section'] = sec
        return boards
    else:
        boards = {}
        sections = []
        for i in initial_data['resourceResponses']:
            if i['name'] == 'BoardFeedResource':
                for boa in i['response']['data']:
                    boards['board'] = boa['board']
                    break

            elif (i['name'] == 'BoardSectionsResource') and (not exclude_section):
                for sec in i['response']['data']:
                    sections.append(sec)
        return boards, sections


def fetch_boards(uname):

    s = get_session(1)
    bookmark = None
    boards = []

    #print('Username: ' + uname)

    #if url != '/mistafisha/animals/':
    #    continue

    while bookmark != '-end-':

        options = {
        'isPrefetch': 'false',
        'privacy_filter': 'all',
        'sort': 'alphabetical', 
        'field_set_key': 'profile_grid_item',
        'username': uname,
        'page_size': 25,
        'group_by': 'visibility',
        'include_archived': 'true',
        'redux_normalize_feed': 'true',
        }

        if bookmark:
            options.update({
                'bookmarks': [bookmark],
            })

        b_len = len(boards) - 1
        if b_len < 0:
            b_len = 0
        # Got end='' here to make flush work
        print('\r[...] Getting all boards [ ' + str(b_len) + ' / ? ]' , end='')
        sys.stdout.flush()

        post_d = urllib.parse.urlencode({
            'source_url': uname,
            'data': {
                'options': options,
                'context': {}
            },
            '_': int(time.time()*1000)
        }).replace('+', '').replace('%27', '%22') \
        .replace('%3A%22true%22', '%3Atrue').replace('%3A%22false%22', '%3Afalse')

        #print('[boards] called headers: ' + repr(s.headers))

        r = s.get('https://www.pinterest.com/resource/BoardsResource/get/', params=post_d, timeout=30)

        #print('[Boards url]: ' + r.url)
        data = r.json()
        #print('res data: ' + repr(data))
        try:
            boards.extend(data['resource_response']['data'])
            bookmark = data['resource']['options']['bookmarks'][0]
        except TypeError: # Normal if invalid username
            cprint(''.join([ HIGHER_RED, '%s' % ('\n[' + x_tag + '] Possible invalid username.\n\n') ]), end='' ) 
            break
    b_len = len(boards)
    print('[' + plus_tag + '] Found {} Board{}.'.format(b_len, 's' if b_len > 1 else ''))

    return boards

# The filesystem limits is 255(normal) or 143((eCryptfs) bytes
# So can't blindly [:] slice without encode first (which most downloaders do the wrong way)
# And need decode back after slice
# And to ensure mix sequence byte in UTF-8 and work
#, e.g. abc𪍑𪍑𪍑
# , need try/catch to skip next full bytes of "1" byte ascii" OR "3 bytes 我" or "4 bytes 𪍑"
# ... by looping 4 bytes(UTF-8 max) from right to left
# HTML5 forbid UTF-16, UTF-16/32 not encourage to use in web page
# So only encode/decode in utf-8
# https://stackoverflow.com/questions/13132976
# https://stackoverflow.com/questions/50385123
# https://stackoverflow.com/questions/11820006
def get_max_path(arg_cut, fs_f_max, fpart_excluded_immutable, immutable):
    #print('before f: ' + fpart_excluded_immutable)
    if arg_cut >= 0:
        fpart_excluded_immutable = fpart_excluded_immutable[:arg_cut]
    if immutable:
        immutable_len = len(immutable.encode('utf-8')) # just in case
    else:
        immutable_len = 0
    space_remains = fs_f_max - immutable_len
    # range([start], stop[, step])
    # -1 step * 4 loop = -4, means looping 4 bytes(UTF-8 max) from right to left
    for gostan in range(space_remains, space_remains - 4, -1):
        try:
            fpart_excluded_immutable = fpart_excluded_immutable.encode('utf-8')[: gostan ].decode('utf-8')
        except UnicodeDecodeError:
            pass #print('Calm down, this is normal: ' + str(gostan) + ' f: ' + fpart_excluded_immutable)
    #print('after f: ' + fpart_excluded_immutable)
    return fpart_excluded_immutable


def get_output_file_path(url, arg_cut, fs_f_max, image_id, human_fname, save_dir):

    pin_id_str = str(image_id)
    basename = os.path.basename(url)
    _, ext = basename.split('.')
    immutable = pin_id_str + '.' +  ext

    fpart_excluded_ext_before  = sanitize( human_fname )
    #print( 'get output f:' + fpart_excluded_ext_before )

    fpart_excluded_ext = get_max_path(arg_cut, fs_f_max, fpart_excluded_ext_before
        , immutable)
        
    if fpart_excluded_ext:
        if fpart_excluded_ext_before == fpart_excluded_ext: # means not truncat
            # Prevent confuse when trailing period become '..'ext and looks like '...'
            if fpart_excluded_ext[-1] == '.':
                fpart_excluded_ext = fpart_excluded_ext[:-1]
        else: # Truncated
            # No need care if two/three/... dots, overkill to trim more and loss information
            if fpart_excluded_ext[-1] == '.':
                fpart_excluded_ext = fpart_excluded_ext[:-1]

            fpart_excluded_ext = get_max_path(arg_cut, fs_f_max, fpart_excluded_ext
                , '...' + immutable)

            fpart_excluded_ext = fpart_excluded_ext + '...'

    file_path = os.path.join(save_dir, '{}'.format( sanitize(pin_id_str + fpart_excluded_ext + '.' +  ext)))
    #print('final f: ' + file_path)
    return file_path


def download_img(image, save_dir, arg_force_update, IMG_SESSION, V_SESSION, arg_cut, fs_f_max):

    try:
        # Using threading.Lock() if necessary
        if 'id' not in image:
            print('\n\nSkip no id\n\n')
            return
        image_id = image['id']

        human_fname = ''
        if ('grid_title' in image) and image['grid_title']:
            human_fname = '_' + image['grid_title']
        # Got case NoneType
        if ('description' in image) and image['description'] and image['description'].strip():
            human_fname = '_'.join((human_fname, image['description'].strip()))
        if ('created_at' in image) and image['created_at']:
            # Don't want ':' become '..' later, so remove ':' early
            img_created_at = image['created_at'].replace(':', '').replace(' +0000', '')
            # Trim `Tue, 01 Sep 2015 011033` to 01Sep2015 to save space in filename
            #, can check log if want details
            img_created_at_l = img_created_at.split(' ')
            if len(img_created_at_l) == 5:
                img_created_at = ''.join(img_created_at_l[1:4])
            human_fname = '_'.join([human_fname, img_created_at])
        # Avoid DD/MM/YYYY truncated when do basename
        # But inside get_output_file_path got sanitize also
        human_fname = human_fname.replace('/', '|').replace(':', '..') 

        #print(human_fname)

        if 'images' in image:
            url = image['images']['orig']['url']

            file_path = get_output_file_path(url, arg_cut, fs_f_max, image_id, human_fname, save_dir)

            try:
                with open(file_path, 'r') as f:
                    pass
            except FileNotFoundError:
                # Will throws OSError first if both FileNotFoundError and OSError met
                # , BUT if folder not exist then will throws FileNotFoundError first
                # But for my code assume folder already there, so can use this trick
                pass
            except OSError: # e.g. File name too long
                cprint(''.join([ HIGHER_RED, '%s %s %s %s%s' % ('\n[' + x_tag + '] Download this image at'
                    , file_path, 'failed :', url, '\n') ]), end='' )
                cprint(''.join([ HIGHER_RED, '%s' % ('\nYou may want to use -c <Maximum length of filename>\n\n') ]), end='' )  
                return quit(traceback.format_exc())

            if not os.path.exists(file_path) or arg_force_update:
                #print(IMG_SESSION.headers)
                
                #url = 'https://httpbin.org/get'
                r = IMG_SESSION.get(url, stream=True, timeout=30)
                
                #print(url + ' ok? '  + str(r.ok))

                if r.ok:
                    #print(r.text)
                    try:
                        with open(file_path, 'wb') as f:
                            for chunk in r:
                                f.write(chunk)

                    except OSError: # e.g. File name too long
                        cprint(''.join([ HIGHER_RED, '%s %s %s %s%s' % ('\n[' + x_tag + '] Download this image at'
                            , file_path, 'failed :', url, '\n') ]), end='' )
                        cprint(''.join([ HIGHER_RED, '%s' % ('\nYou may want to use -c <Maximum length of filename>\n\n') ]), end='' )  
                        return quit(traceback.format_exc())

                else:
                    #cprint(''.join([ HIGHER_RED, '%s %s %s %s%s' % ('\n[' + x_tag + '] Download this image at'
                    #, file_path, 'failed :', url, '\n') ]), end='' )
                    imgDimens = []
                    imgDimensD = {}
                    for ik, iv in image['images'].items():
                        if 'x' in ik:
                            imgDimens.append(iv['width'])
                            imgDimensD[iv['width']] =  iv['url']
                    if imgDimens:
                        imgDimens.sort(key=int)
                        url = imgDimensD[int(imgDimens[-1])]
                        #double \n\n to make if unlikely same line behind thread progress bar
                        #cprint('\n\n[...] Retry with second best quality url: {}'.format(url), attrs=BOLD_ONLY)

                        file_path = get_output_file_path(url, arg_cut, fs_f_max, image_id, human_fname, save_dir)
                        
                        if not os.path.exists(file_path) or arg_force_update:
                            r = IMG_SESSION.get(url, stream=True, timeout=30)
                            if r.ok:

                                try:
                                    with open(file_path, 'wb') as f:
                                        for chunk in r:
                                            f.write(chunk)
                                except OSError: # e.g. File name too long
                                    cprint(''.join([ HIGHER_RED, '%s %s %s %s%s' % ('\n[' + x_tag + '] Retried this image at'
                                        , file_path, 'failed :', url, '\n') ]), end='' )
                                    cprint(''.join([ HIGHER_RED, '%s' % ('\nYou may want to use -c <Maximum length of filename>\n\n') ]), end='' )  
                                    return quit(traceback.format_exc())

                                #print('\n\n[' + plus_tag + '] ', end='') # konsole has issue if BOLD_ONLY with cprint with plus_tag
                                # Got case replace /originals/(detected is .png by imghdr)->covert to .png replace 736x bigger size than orig's png (but compare quality is not trivial), better use orig as first choice
                                # e.g. https://www.pinterest.com/antonellomiglio/computer/ 's https://i.pinimg.com/736x/3d/f0/88/3df088200b94f0b6b8325ae0a118b401--apple-computer-next-computer.jpg
                                #cprint('\nRetried with second best quality url success :D {} saved to {}\n'.format(url, file_path), attrs=BOLD_ONLY)
                            else:
                                cprint(''.join([ HIGHER_RED, '%s %s %s %s%s' % ('\n[' + x_tag + '] Retried this image at'
                                , file_path, 'failed :', url, '\n') ]), end='' )
                        else:
                            pass #cprint('\nFile at {} already exist.\n'.format(file_path), attrs=BOLD_ONLY)

        else: 
            pass #print('No image found in this image index. This is normal (may be 1))')

        if ('videos' in image) and image['videos']: # image['videos'] may None
            v_d = image['videos']['video_list']
            vDimens = []
            vDimensD = {}
            for v_format, v_v in v_d.items():
                if 'url' in v_v and v_v['url'].endswith('mp4'):
                    vDimens.append(v_v['width'])
                    vDimensD[v_v['width']] =  v_v['url']
            if vDimens:
                vDimens.sort(key=int)
                vurl = vDimensD[int(vDimens[-1])]
                #cprint('\n\n[...] Try with best quality video: {}'.format(vurl), attrs=BOLD_ONLY)

                file_path = get_output_file_path(vurl, arg_cut, fs_f_max, image_id, human_fname, save_dir)
                #print(file_path)

                # We MUST get correct file_path first to avoid final filename != trimmed filename
                # ... which causes `not os.path.exists(file_path)` failed and re-download

                if not os.path.exists(file_path) or arg_force_update:
                    
                    r = V_SESSION.get(vurl, stream=True, timeout=30)
                    
                    #print(vurl + ' ok? '  + str(r.ok))

                    if r.ok:
                        #print(r.text)
                        try:
                            with open(file_path, 'wb') as f:
                                for chunk in r:
                                    f.write(chunk)
                        except OSError: # e.g. File name still too long
                            cprint(''.join([ HIGHER_RED, '%s %s %s %s%s' % ('\n[' + x_tag + '] Download this video at'
                                , save_dir, 'failed :', vurl, '\n') ]), end='' )
                            cprint(''.join([ HIGHER_RED, '%s' % ('\nYou may want to use -c <Maximum length of filename>\n\n') ]), end='' )  
                            return quit(traceback.format_exc()) 

                    else:
                        cprint(''.join([ HIGHER_RED, '%s %s %s %s%s' % ('\n[' + x_tag + '] Download this video at'
                            , save_dir, 'failed :', vurl, '\n') ]), end='' )

    except: # Need catch inside job, or else it doesn't throws
        print()
        return quit(traceback.format_exc())


def create_dir(save_dir):

    try:
        os.makedirs(save_dir)
    except FileExistsError: # Check this first to avoid OSError cover this
        pass # Normal if re-download
    except OSError: # e.g. File name too long 

        # Only need to care for individual path component
        #, i.e. os.statvfs('./').f_namemax - 1 = 255(normal fs) or 143(eCryptfs) )
        #, not full path( os.statvfs('./').f_frsize - 1 = 2045)
        # Overkill seems even you do extra work to truncate path, then what if user give arg_dir at
        # ... 2045th path? how is it possible create new dir/file from that point?
        # So only need to care for individual component 
        #... which max total(estimate) is uname 100 + (boardname 50*4)+( section 50*3) = ~450 bytes only.
        # Then add max file 255 - 705, still far away from 2045th byte(or 335 4_bytes utf-8)
        # So you direct throws OSError enough to remind that user don't make insane fs hier

        cprint(''.join([ HIGHER_RED, '%s' % ('\nIt might causes by too long(2045 bytes) in full path.\
        You may want to to use -d <other path> OR -c <Maximum length of filename>.\n\n') ]), end='' )  
        raise

def write_log(arg_timestamp_log, save_dir, images, pin):

    got_img = False
    
    if arg_timestamp_log:
        if pin:
            log_timestamp = 'log-pinterest-downloader_' + str(pin) + '_' + datetime.now().strftime('%Y-%m-%d %H.%M.%S')
        else: # None
            log_timestamp = 'log-pinterest-downloader_' + datetime.now().strftime('%Y-%m-%d %H.%M.%S')
    else:
        if pin:
            log_timestamp = 'log-pinterest-downloader_' + str(pin)
        else:
            log_timestamp = 'log-pinterest-downloader'
    log_path = os.path.join(save_dir, '{}'.format( sanitize(log_timestamp + '.log' )))
    #print('log_path: ' + log_path)

    if images:
        with open(log_path, 'w') as f: # Reset before append
            f.write('Pinterest Downloader: Version 1.1\n\n') # Easy to recognize if future want to change something
        skipped_total = 0
        for log_i, image in enumerate(images):
            if 'id' not in image:
                skipped_total+=1
                continue
            got_img = True
            image_id = image['id']
            #print('got img: ' + image_id) # Possible got id but empty section
            #, so still failed to use got_img to skip showing estimated 1 image if actually empty
            story = ''
            #print(image)
            #print(image_id)
            # if use 'title' may returns dict {'format': 'Find more ideas', 'text': None, 'args': []}
            if ('grid_title' in image) and image['grid_title']:
                story = '\nTitle: ' + image['grid_title']
            # Got case NoneType
            if ('description' in image) and image['description'] and image['description'].strip():
                story += '\nDescription: ' + image['description'].strip()
            if ('created_at' in image) and image['created_at']:
                story += '\nCreated at: ' + image['created_at']
            if ('link' in image) and image['link']:
                story += ('\nLink: ' + image['link'])
            if ('rich_metadata' in image) and image['rich_metadata']:
                story += ('\n\nMetadata: ' + repr(image['rich_metadata']))
            if story:
                try:
                    # Windows need utf-8
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write('[ ' + str(log_i + 1 - skipped_total) + ' ] Pin Id: ' + str(image_id) + '\n')
                        f.write(story + '\n\n')
                except OSError: # e.g. File name too long
                    cprint(''.join([ HIGHER_RED, '%s' % ('\nYou may want to use -c <Maximum length of filename>\n\n') ]), end='' )  
                    return quit(traceback.format_exc())
            else:
                skipped_total+=1
                continue

    return got_img

def sanitize(path):
    # trim multiple whitespaces
    if IS_WIN:
        return os.path.basename( path.replace('  ', ' ').replace('/', '_').replace('\\', '_').replace(':', '..').strip() )
    else:
        return os.path.basename( path.replace('  ', ' ').replace('/', '|').replace(':', '..').strip() )

def fetch_imgs(board, uname, board_name, section, arg_timestamp, arg_timestamp_log, arg_force_update
    , arg_dir, arg_thread_max, IMGS_SESSION, IMG_SESSION, V_SESSION, arg_cut, fs_f_max):
    
    bookmark = None
    images = []
    
    if arg_timestamp:
        timestamp_d = '_' + datetime.now().strftime('%Y-%m-%d %H.%M.%S') + '.d'
    else:
        timestamp_d = ''
    try:
        if 'owner' in board:
            #uname = board['owner']['username']
            #save_dir = os.path.join(arg_dir, uname, board['name'] + timestamp_d)
            #url = board['url']
            bid = board['id']
            # Might unicode, so copy from web browser become %E4%Bd 
            #... which is not the board filename I want
            board_name_folder = board['name']
        elif 'board' in board:
            #uname = board['pinner']['username']
            #save_dir = os.path.join(arg_dir, uname, board['board']['name'] + timestamp_d)
            #url = board['board']['url']
            bid = board['board']['id']
            board_name_folder = board['board']['name']
            #print(board_name_folder)
            if section:
                section_folder = board['section']['title']
                section_id = board['section']['id']
        else:
            return quit('{}'.format('\n[' + x_tag + '] No item found.\n\
Please ensure your username/boardname or link has media item.\n') )
    except (KeyError, TypeError):
        url = '/'.join((uname, board_name))
        cprint(''.join([ HIGHER_RED, '%s %s %s' % ('\n[' + x_tag + '] Failed. URL:', url, '\n\n') ]), end='' )
        return quit(traceback.format_exc() + '\n[!] Something wrong with Pinterest URL. Please report this issue at https://github.com/limkokhole/pinterest-downloader/issues , thanks.') 

    if section:
        # Put -1 fot arg_cut arg bcoz don't want cut on directory
        # to avoid cut become empty (or provide new arg -c-cut-directory
        # , but overcomplicated and in reality who want to cut dir?
        # ... Normally only want cut filename bcoz of included title/description )
        save_dir = os.path.join( arg_dir,  get_max_path(-1, fs_f_max, sanitize(uname), None)
            , get_max_path(-1, fs_f_max, sanitize(board_name_folder + timestamp_d), None)
            , get_max_path(-1, fs_f_max, sanitize(section_folder), None) )
        url = '/' + '/'.join((uname, board_name, section)) + '/'
    else:
        save_dir = os.path.join( arg_dir,  get_max_path(-1, fs_f_max, sanitize(uname), None)
            , get_max_path(-1, fs_f_max, sanitize(board_name_folder + timestamp_d), None))
        # If boardname in url is lowercase but title startswith ' which quotes to %22 and cause err
        #... So don't use board_name_folder as board_name in url below to call API
        url = '/'.join((uname, board_name))

    #if not section:
    #   print('[Board id]: '+ repr(bid)) 

    while bookmark != '-end-':

        if section:

            options = {
            'isPrefetch': 'false',
            'field_set_key': 'react_grid_pin',
            'is_own_profile_pins': 'false',
            'page_size': 25,
            'redux_normalize_feed': 'true',
            'section_id': section_id,
            }

        else:
            options = {
            'isPrefetch': 'false',
            'board_id': bid,
            'board_url': url,
            'field_set_key': 'react_grid_pin',
            'filter_section_pins': 'true', 
            'sort': 'default',
            'layout':'default',
            'page_size': 25,
            'redux_normalize_feed': 'true',
            }

        if bookmark:
            options.update({
                'bookmarks': [bookmark],
            })

        i_len = len(images) - 1
        if i_len < 0:
            i_len = 0
        # Got end='' here also not able make flush work
        if section:
            print('\r[...] Getting all images in this section: {}/{} ... [ {} / ? ]'
                .format(board_name, section, str(i_len)), end='')
        else:
            print('\r[...] Getting all images in this board: {} ... [ {} / ? ]'
                .format(board_name, str(i_len)), end='')
        sys.stdout.flush()

        post_d = urllib.parse.urlencode({
            'source_url': url,
            'data': {
                'options': options,
                'context': {}
            },
            '_': int(time.time()*1000)
        }).replace('+', '').replace('%27', '%22') \
        .replace('%3A%22true%22', '%3Atrue').replace('%3A%22false%22', '%3Afalse')

        #print(post_d)
        #print('[imgs] called headers: ' + repr(IMGS_SESSION.headers))

        if section:
            r = IMGS_SESSION.get('https://www.pinterest.com/resource/BoardSectionPinsResource/get/'
                , params=post_d, timeout=30)
        else:
            r = IMGS_SESSION.get('https://www.pinterest.com/resource/BoardFeedResource/get/'
                , params=post_d, timeout=30)

        #print('Imgs url ok: ' + str(r.ok))
        #print('Imgs url: ' + r.url)
        data = r.json()
        # Useful for debug with print only specific id log
        #if 'e07614d79a22d22c83d51649e2e01e43' in repr(data):
        #print('res data: ' + repr(data))
        images.extend(data['resource_response']['data'])

        bookmark = data['resource']['options']['bookmarks'][0]

    create_dir(save_dir)
    got_img = write_log(arg_timestamp_log, save_dir, images, None)

    if got_img:
        # From what I observed, always got extra index is not media, so better -1
        # And no point to loop above and detect early, overkill
        print(' [' + plus_tag + '] Found estimated {} images'.format(len(images) - 1))
    else: # empty section
        print('\n[i] No item found.')
        return

    if arg_thread_max < 1:
        arg_thread_max = None # Use default: "number of processors on the machine, multiplied by 5"
    with ThreadPoolExecutor(max_workers = arg_thread_max) as executor:

        # Create threads
        futures = {executor.submit(download_img, image, save_dir, arg_force_update
                , IMG_SESSION, V_SESSION, arg_cut, fs_f_max) for image in images}

        # as_completed() gives you the threads once finished
        for index, f in enumerate(as_completed(futures)):
            # Get the results
            # rs = f.result()
            # print('done')
            printProgressBar(index + 1, len(images), prefix='[...] Downloading:'
                , suffix='Complete', length=50)

    # Need suffix with extra 3 spaces to replace previos longer ... + Downloading->ed line
    # ... to avoid see wrong word "Complete"
    printProgressBar(len(images), len(images), prefix='[' + done_tag + '] Downloaded:'
        , suffix='Complete   ', length=50)

    print()


def main():

    start_time = int(time.time())

    arg_parser = argparse.ArgumentParser(description='Download ALL board/section from ' + pinterest_logo +  'interest by username, username/boardname, username/boardname/section or link. Support image and video.\n\
        Filename compose of PinId_Title_Description_Date.Ext. PinId always there while the rest is optional.\n\
        If filename too long will endswith ... and you can check details in log-pinterest-downloader.log file.')
    arg_parser.add_argument('path', nargs='?', help='Pinterest username, or username/boardname, or link( /pin/ may include created time )')
    arg_parser.add_argument('-d', '--dir', dest='dir', type=str, default='images', help='Specify folder path/name to store. Default is "images"')
    arg_parser.add_argument('-j', '--job', dest='thread_max', type=int, default=0, help='Specify maximum threads when downloading images. Default is number of processors on the machine, multiplied by 5')
    # Username or Boardname might longer than 255 bytes
    # Username max is 100(not allow 3 bytes unicode)
    # Section/Boardname(Title) max are 50(count as singe char(i.e. 3 bytes unicode same as 1 byte ASCII), not bytes)
    # Board not possible create 4 bytes UTF-8 (become empty // or trim, lolr)
    # Description is 500, source_url(link) is 2048 (but not able save even though no error)
    # Pin Title is max 100 , which emoji count as 2 bytes per glyph (Chinese char still count as 1 per glyph)
    # [UPDATE] now --cut is per glyph, not byte, which is most users expected
    #, whereas bytes should detect by program (244/143) or raise by simply use -c <short value> to solve
    arg_parser.add_argument('-c', '--cut', type=int, default=-1, help='Specify maximum length of "_TITLE_DESCRIPTION_DATE"(exclude ...) in filename.')
    arg_parser.add_argument('-bt', '--board-timestamp', dest='board_timestamp', action='store_true', help='Suffix board directory name with unique timestamp')
    arg_parser.add_argument('-lt', '--log-timestamp', dest='log_timestamp', action='store_true', help='Suffix log-pinterest-downloader.log filename with unique timestamp. Default filename is log-pinterest-downloader.log.\n\
        Note: Pin id without Title/Description/Link/Metadata/Created_at will not write to log.')
    arg_parser.add_argument('-f', '--force', action='store_true', help='Force re-download even if image already exist')
    arg_parser.add_argument('-es', '--exclude-section', dest='exclude_section', action='store_true', help='Exclude sections if download from username or board.')
    try:
        args, remaining  = arg_parser.parse_known_args()
    except SystemExit: # Normal if --help, catch here to avoid main() global ex catch it
        return
    if remaining:
        return quit( ['You type redundant options: ' + ' '.join(remaining)
            , 'Please check your command or --help to see options manual.' ])

    if not args.path:
        args.path = input('Username/Boardname/Section or Link: ').strip()
    if not args.path:
        return quit('Path cannot be empty. ')

    url_path = args.path.strip().split('?')[0].split('#')[0]
    # Convert % format of unicode url when copied from Firefox 
    # This is important especially section need compare the section name later
    url_path = urllib.parse.unquote_plus(url_path) 
    if url_path.endswith('/'):
        url_path = url_path[:-1]
    if '://' in url_path:
        url_path = '/'.join(url_path.split('://')[1:][0].split('/')[1:])
        if not url_path:
            return quit('{} {} {}'.format('\n[' + x_tag + '] Neither username/boardname nor valid link: ', args.path, '\n') )
    if url_path.startswith('/'):
        url_path = url_path[1:]
    slash_path = url_path.split('/')
    if '.' in slash_path[0]:
        # Impossible dot in username, so it means host without https:// and nid remove
        slash_path = slash_path[1:]
    if len(slash_path) > 3:
        return quit('[!] Something wrong with Pinterest URL. Please report this issue at https://github.com/limkokhole/pinterest-downloader/issues , thanks.') 

    fs_f_max = None
    #  255 bytes is normaly fs max, 143 bytes is eCryptfs max
    # https://unix.stackexchange.com/questions/32795/
    # To test eCryptfs: https://unix.stackexchange.com/questions/426950/
    for fs_f_max_i in (255, 143):
        try:
            with open('A'*fs_f_max_i, 'r') as f:
                fs_f_max = fs_f_max_i # if got really this long A exists will come here
                break
        except FileNotFoundError:
            # Will throws OSError first if both FileNotFoundError and OSError met
            # , BUT if folder not exist then will throws FileNotFoundError first
            # But current directory already there, so can use this trick
            # In worst case just raise it
            fs_f_max = fs_f_max_i # Normally came here in first loop
            break
        except OSError: # e.g. File name too long
            pass #print('Try next') # Or here first if eCryptfs
    #print('fs filename max len is ' + repr(fs_f_max))
    # https://github.com/ytdl-org/youtube-dl/pull/25475
    # https://stackoverflow.com/questions/54823541/what-do-f-bsize-and-f-frsize-in-struct-statvfs-stand-for
    if fs_f_max is None: # os.statvfs ,ay not avaiable in Windows, so lower priority
        #os.statvfs('.').f_frsize - 1 = 4095 # full path max bytes
        fs_f_max = os.statvfs('.').f_namemax

    if len(slash_path) == 2:
        # may copy USERNAME/boards/ links
        if slash_path[-1].strip() == 'boards':
            slash_path = slash_path[:-1]
        elif slash_path[-2].strip() == 'pin':
            print('[i] Job is download video/image of single pin page.')
            pin_id = slash_path[-1] #bk first before reset 
            slash_path = [] # reset for later in case exception
            get_pin_info(pin_id.strip(), args.log_timestamp, args.force, args.dir, args.cut, fs_f_max)

    if len(slash_path) == 3:
        u_url = '/'.join(slash_path)
        print('[i] Job is download single board by username/boardname/section: {}'.format(u_url))
        # Will err if try to create section by naming 'more_ideas'
        if ( slash_path[-3] in ('search', 'categories', 'topics') ) or ( slash_path[-1] in ['more_ideas'] ):
            return quit('{}'.format('\n[' + x_tag + '] Search, Categories, Topics, more_ideas are not supported.\n') )
        board = get_board_info(u_url, False, slash_path[-1]) # need_get_section's True/False not used
        try: 
            IMGS_SESSION = get_session(2)
            IMG_SESSION = get_session(3)
            V_SESSION = get_session(4)
            fetch_imgs( board, slash_path[-3], slash_path[-2], slash_path[-1], args.board_timestamp
                , args.log_timestamp, args.force, args.dir, args.thread_max
                , IMGS_SESSION, IMG_SESSION, V_SESSION, args.cut, fs_f_max )
        except KeyError:
            return quit(traceback.format_exc())

    elif len(slash_path) == 2:
        u_url = '/'.join(slash_path)
        print('[i] Job is download single board by username/boardname: {}'.format(u_url))
        if slash_path[-2] in ('search', 'categories', 'topics'):
            return quit('{}'.format('\n[' + x_tag + '] Search, Categories and Topics not supported.\n') )
        board, sections = get_board_info(u_url, args.exclude_section, None)
        try: 
            IMGS_SESSION = get_session(2)
            IMG_SESSION = get_session(3)
            V_SESSION = get_session(4)
            fetch_imgs( board, slash_path[-2], slash_path[-1], None, args.board_timestamp, args.log_timestamp, args.force
            , args.dir, args.thread_max, IMGS_SESSION, IMG_SESSION, V_SESSION, args.cut, fs_f_max )
            if sections:
                sec_c = len(sections)
                print('[i] Trying to get ' + str(sec_c) + ' section{}'.format('s' if sec_c > 1 else ''))
                for sec in sections:
                    s_url = u_url + '/' + sec['slug']
                    board = get_board_info(s_url, False, sec['slug']) # False not using bcoz sections not [] already
                    fetch_imgs( board, slash_path[-2], slash_path[-1], sec['slug'], args.board_timestamp
                        , args.log_timestamp, args.force, args.dir, args.thread_max
                        , IMGS_SESSION, IMG_SESSION, V_SESSION, args.cut, fs_f_max )

        except KeyError:
            return quit(traceback.format_exc())

    elif len(slash_path) == 1:
        print('[i] Job is download all boards Job is download all boards by username: {}'.format(slash_path[-1]))
        if slash_path[-1] in ('search', 'categories', 'topics'):
            return quit('{}'.format('\n[' + x_tag + '] Search, Categories and Topics not supported.\n') )
        #boards = get_user_boards( slash_path[-1] )
        try: 
            boards = fetch_boards( slash_path[-1] )
            IMGS_SESSION = get_session(2)
            IMG_SESSION = get_session(3)
            V_SESSION = get_session(4)
            # Multiple logs saved inside relevant board dir
            for index, board in enumerate(boards):
                if 'name' not in board:
                    print('Skip no name')
                    continue

                board_name = board['name']
                board['owner']['id'] = board['id']
                fetch_imgs( board, slash_path[-1], board_name, None, args.board_timestamp, args.log_timestamp
                    , args.force, args.dir, args.thread_max, IMGS_SESSION, IMG_SESSION, V_SESSION
                    , args.cut, fs_f_max )
                if (not args.exclude_section) and (board['section_count'] > 0):
                    sec_c = board['section_count']
                    print('[i] Trying to get ' + str(sec_c) + ' section{}'.format('s' if sec_c > 1 else ''))
                    u_url = board['url'] 
                    # E.g. /example/commodore-computers/ need trim to example/commodore-computers
                    if u_url[-1] == '/': 
                        u_url = u_url[:-1]
                    if u_url[0] == '/':
                        u_url = u_url[1:]
                    # ags.es placeholder below always False bcoz above already check (not args.exclude_section) 
                    board, sections = get_board_info(u_url, False, None)
                    for sec in sections:
                        s_url = u_url + '/' + sec['slug']
                        board = get_board_info(s_url, False, sec['slug']) 
                        sec_uname, sec_bname = u_url.split('/')
                        fetch_imgs( board, sec_uname, sec_bname, sec['slug'], args.board_timestamp
                            , args.log_timestamp, args.force, args.dir, args.thread_max
                            , IMGS_SESSION, IMG_SESSION, V_SESSION, args.cut, fs_f_max )

        except KeyError:
            return quit(traceback.format_exc())

    end_time = int(time.time())
    print('[i] Time Spent: ' + str(timedelta(seconds= end_time - start_time)))
    

if __name__ == '__main__':
    try:
        main()
    except requests.exceptions.ReadTimeout:
        cprint(''.join([ HIGHER_RED, '{}'.format('\n[' + x_tag + '] Suddenly not able to connect. Please check your network.\n') ]), end='' )
        quit('')
    except requests.exceptions.ConnectionError:
        cprint(''.join([ HIGHER_RED, '{}'.format('\n[' + x_tag + '] Not able to connect. Please check your network.\n') ]), end='' )
        quit('')
    except:
        quit(traceback.format_exc())

