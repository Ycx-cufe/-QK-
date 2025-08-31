from flask import Flask, render_template, request, jsonify
import requests
import time
import json
import re
import threading

app = Flask(__name__)

# ==========================================================
#                      用户配置区 (无需修改)
# ==========================================================
# 在线版不需要在这里填写个人信息，而是通过网页输入
# URL信息
base_url = 'https://xuanke.cufe.edu.cn'
login_url = f'{base_url}/jwglxt/xtgl/login_slogin.html'
course_data_api_url = f'{base_url}/jwglxt/xsxk/zzxkyzb_cxZzxkYzbPartDisplay.html?gnmkdm=N253512'
select_course_api_url = f'{base_url}/jwglxt/xsxk/zzxkyzbjk_xkBcZyZzxkYzb.html?gnmkdm=N253512'

# 课程查询的完整payload
search_payload_template = {
    'filter_list[0]': '',
    'rwlx': '1',
    'xklc': '2',
    'xkly': '1',
    'bklx_id': '0',
    'sfkkjyxdxnxq': '0',
    'kzkcgs': '0',
    'xqh_id': '2',
    'jg_id': '07',
    'njdm_id_1': '2023',
    'zyh_id_1': '0704',
    'gnjkxdnj': '0',
    'zyh_id': '0704',
    'zyfx_id': 'wfx',
    'njdm_id': '2023',
    'bh_id': '07042302',
    'bjgkczxbbjwcx': '0',
    'xbm': '1',
    'xslbdm': '1',
    'mzm': '01',
    'xz': '4',
    'ccdm': '3',
    'xsbj': '0',
    'sfkknj': '1',
    'sfkkzy': '1',
    'kzybkxy': '0',
    'sfznkx': '0',
    'zdkxms': '0',
    'sfkxq': '0',
    'njdm_id_xs': '2023',
    'zyh_id_xs': '0704',
    'sfkcfx': '0',
    'kkbk': '0',
    'kkbkdj': '0',
    'bklbkcj': '0',
    'sfkgbcx': '0',
    'sfrxtgkcxd': '0',
    'tykczgxdcs': '0',
    'xkxnm': '2025',
    'xkxqm': '3',
    'kklxdm': '01',
    'bbhzxjxb': '0',
    'xkkz_id': '3CE1DFBBD8AC4FA1E06315330D0A862A',
    'rlkz': '0',
    'xkzgbj': '0',
    'kspage': '1',
    'jspage': '10',
    'jxbzb': '',
    'gnmkdm': 'N253512',
    'layout': 'default'
}

# 用于存储正在进行的抢课任务
running_tasks = {}

# 核心抢课逻辑
def grab_course_logic(username, password, course_name, target_jxb_id, course_total_capacity):
    session = requests.Session()
    login_payload = {'yhm': username, 'mm': password}
    
    # 登录部分，省略打印，直接返回登录结果
    try:
        session.get(login_url)
        login_response = session.post(login_url, data=login_payload)
        
        if "layout" not in login_response.url and "选课" not in login_response.text:
            return {"success": False, "msg": "登录失败，请检查账号密码。"}
    except requests.exceptions.RequestException:
        return {"success": False, "msg": "登录时发生网络错误。"}
    
    # 循环抢课
    while True:
        try:
            search_payload = search_payload_template.copy()
            search_payload['filter_list[0]'] = course_name
            
            course_data_response = session.post(course_data_api_url, data=search_payload)
            
            if course_data_response.status_code != 200:
                time.sleep(5)
                continue
            
            try:
                course_list_data = course_data_response.json()
            except json.JSONDecodeError:
                time.sleep(5)
                continue
            
            if 'tmpList' not in course_list_data:
                time.sleep(5)
                continue
                
            for course in course_list_data.get('tmpList', []):
                if course_name in course.get('kcmc', ''):
                    
                    selected_students = int(course.get('yxzrs'))
                    remaining_count = course_total_capacity - selected_students
                    
                    if target_jxb_id and target_jxb_id != course.get('jxb_id'):
                        continue
                    
                    if remaining_count > 0:
                        select_payload = {
                            'jxb_ids': course.get('jxb_id'),
                            'kch_id': course.get('kch_id'),
                            'kcmc': course.get('kcmc'),
                            'rwlx': '1', 'rlkz': '0', 'cdrlkz': '0', 'rlzlkz': '1', 'sxbj': '1', 'xxkbj': '0', 'qz': '0', 'cxbj': '0',
                            'xkkz_id': search_payload.get('xkkz_id'), 'njdm_id': search_payload.get('njdm_id'),
                            'zyh_id': search_payload.get('zyh_id'), 'njdm_id_xs': search_payload.get('njdm_id_xs'),
                            'zyh_id_xs': search_payload.get('zyh_id_xs'), 'kklxdm': search_payload.get('kklxdm'),
                            'xklc': search_payload.get('xklc'), 'xkxnm': search_payload.get('xkxnm'),
                            'xkxqm': search_payload.get('xkxqm'), 'jcxx_id': None,
                        }
                        
                        select_response = session.post(select_course_api_url, data=select_payload)
                        
                        try:
                            select_result = select_response.json()
                            if select_result.get('flag') == '1':
                                return {"success": True, "msg": f"课程 '{course_name}' 选课成功！"}
                            else:
                                return {"success": False, "msg": f"选课失败：{select_result.get('msg', '未知错误')}"}
                        except json.JSONDecodeError:
                            return {"success": False, "msg": "选课API返回了非JSON响应。"}
            
            time.sleep(5)
        
        except Exception as e:
            return {"success": False, "msg": f"发生错误: {e}"}

# 网站主页
@app.route('/')
def index():
    return render_template('index.html')

# API：查询课程信息
@app.route('/api/query', methods=['POST'])
def query_course():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    course_name = data.get('course_name')
    
    if not all([username, password, course_name]):
        return jsonify({"success": False, "msg": "参数不完整。"})

    search_payload = search_payload_template.copy()
    search_payload['filter_list[0]'] = course_name
    
    session = requests.Session()
    login_payload = {'yhm': username, 'mm': password}
    
    try:
        session.get(login_url)
        login_response = session.post(login_url, data=login_payload)
        
        if "layout" not in login_response.url and "选课" not in login_response.text:
            return jsonify({"success": False, "msg": "登录失败，请检查账号密码。"})

        course_data_response = session.post(course_data_api_url, data=search_payload)
        
        if course_data_response.status_code != 200:
            return jsonify({"success": False, "msg": "获取课程数据失败。"})
            
        return jsonify(course_data_response.json())
    
    except Exception as e:
        return jsonify({"success": False, "msg": f"发生错误: {e}"})

# API：开始抢课
@app.route('/api/start_grab', methods=['POST'])
def start_grab():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    course_name = data.get('course_name')
    target_jxb_id = data.get('target_jxb_id')
    course_total_capacity = int(data.get('course_total_capacity', 0))
    
    if not all([username, password, course_name, target_jxb_id, course_total_capacity]):
        return jsonify({"success": False, "msg": "参数不完整。"})
    
    # 使用线程在后台运行抢课任务
    task_id = threading.Thread(target=grab_course_logic, args=(username, password, course_name, target_jxb_id, course_total_capacity))
    task_id.start()
    
    return jsonify({"success": True, "msg": "抢课任务已在后台启动！"})


if __name__ == '__main__':
    app.run(debug=True)