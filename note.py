#!/home/hf/python_env/bin/python
# coding:utf-8

import sys
import logging
import markdown
import os

config = {
    'target_path_prefix': '/home/hf/all-src-here/normal_projects/normal_frontend/normal_portal/pages/blog/',
    'list_page_path_prefix': '/home/hf/all-src-here/normal_projects/normal_frontend/normal_portal/pages/blog/'
}

command = sys.argv[1]
opt = sys.argv[2]
md_files = sys.argv[3:]

if command != 'create':
    logging.error('unkown command:' + command)
    sys.exit(0)

if opt != '-f':
    logging.error('unkown opts:' + opt)
    sys.exit(0)

if len(md_files) == 0:
    logging.error('file names not provided')
    sys.exit(0)

md = markdown.Markdown()
os.system('touch temp')
md_file_names = []
for md_file_name in md_files:
    md_file_name = str(md_file_name)
    # convert into temp file
    md.convertFile(md_file_name, 'temp')
    md.reset()
    md_file_name = md_file_name[md_file_name.rfind('/') + 1:]

    # create html file
    md_file_name = md_file_name.split('.')[0]
    md_file_names.append(md_file_name)
    html_file_name = config.get('target_path_prefix') + md_file_name + '.html'
    os.system('touch %s' % html_file_name)
    html_file = open(html_file_name, mode='w')

    # convert and write
    for line in open('note_template'):
        if line.find('$') > -1:
            for convert_line in open('temp'):
                html_file.write(convert_line)
            html_file.write('\n')
        else:
            html_file.write(line)

    html_file.close()
    os.system('rm -rf temp')

# append link in list page
list_page_name = config.get('list_page_path_prefix') + 'notes_list.html'
list_page_tmp_name = config.get('list_page_path_prefix') + 'notes_list.html.tmp'
os.system('mv %s %s' % (list_page_name, list_page_tmp_name))
os.system('touch %s' % list_page_name)

new_list_page = open(list_page_name, mode='w')
for line in open(list_page_tmp_name):
    if line.find('<h3>笔记归档</h3>') > -1:
        new_list_page.write(line)
        for md in md_file_names:
            new_list_page.write('<p><a href="%s">%s</a></p>' % (md + '.html', md))
            new_list_page.write('\n')
    else:
        new_list_page.write(line)
os.system('rm %s' % list_page_tmp_name)
