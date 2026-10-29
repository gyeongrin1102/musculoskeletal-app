import hashlib
import hmac
import io
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from core import Opening,TYPES,blank,normalize_rows,load_page,annotate,png_bytes
from cloud_store import Store,StoreError
from register import assign_names,xlsx_bytes
from ocr_engine import detect_local
from ui_views import simple_rows,drawing,detail
from inspection_ui import inspections_page,revision_ui,load_records
from inspection_logic import status
from dashboard_ui import render_dashboard
from actions_ui import actions_page,action_status
from report_export import report_page
from mobile_ui import use_mobile,mobile_page,set_view
from html import escape
import streamlit as st

SITE='부산 문현마루지역주택조합 공동주택 신축사업'
NAV=[('종합현황',':material/bar_chart:'),('도면·개구부',':material/description:'),('안전점검',':material/fact_check:'),('사진·조치',':material/photo_library:'),('보고서',':material/assignment:')]


def styles():
    st.markdown('''<style>
html,body,[data-testid="stApp"],button,input,textarea,select{font-family:'Malgun Gothic','맑은 고딕',Arial,sans-serif}
[data-testid="stApp"],[data-testid="stAppViewContainer"]{background:#fff!important;color:#17212b!important;color-scheme:light}
/* Remove the opaque fixed toolbar that masks content during scrolling. */
[data-testid="stHeader"]{background:transparent!important;border:0!important;height:0!important;min-height:0!important;pointer-events:none}
[data-testid="stToolbar"]{display:none!important}
[data-testid="stHeader"] button,[data-testid="stSidebarCollapsedControl"]{pointer-events:auto}
[data-testid="stApp"]::before{content:"";position:fixed;top:0;left:0;right:0;height:5px;background:#2455a4;z-index:999990;pointer-events:none}
.block-container{max-width:1800px;padding:3.6rem 1.6rem 2rem!important}
[data-testid="stMainBlockContainer"]>[data-testid="stVerticalBlock"]{gap:.65rem}
/* Zero-height login bridge must not leave a grid gap above the page. */
[data-testid="stElementContainer"]:has(iframe[title*="opening_remember_device"]){height:0!important;min-height:0!important;margin:0!important}
[data-testid="stSidebar"]{background:#fff!important;border-right:1px solid #d5dce5;min-width:240px;max-width:260px;color:#17212b!important}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding:.5rem .85rem 1rem!important}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.4rem}
[data-testid="stSidebar"] button{width:100%;justify-content:flex-start;min-height:44px;border:0;border-radius:4px;background:transparent;padding:9px 14px;box-shadow:none}
[data-testid="stSidebar"] button p,[data-testid="stSidebar"] button span{color:#182536!important;font-size:16px!important;font-weight:650!important}
[data-testid="stSidebar"] button:hover{background:#edf3fc!important}
[data-testid="stSidebar"] button[kind="primary"]{background:#e6eefb!important;border-left:4px solid #2455a4!important}
[data-testid="stSidebar"] button[kind="primary"] p,[data-testid="stSidebar"] button[kind="primary"] span{color:#194c99!important}
.shell-brand{display:flex;gap:10px;align-items:flex-start;margin:0 0 16px;color:#152b46;font-size:20px;line-height:1.35;font-weight:750}
.shell-brand small{display:block;font-size:14px;color:#415269;font-weight:600;margin-top:6px}
.shell-site-row{display:flex;justify-content:space-between;align-items:center;gap:12px;border-bottom:1px solid #d8e0ec;padding-bottom:10px;margin-bottom:12px}.shell-user{flex-shrink:0;color:#172b46;font-size:15px;font-weight:700;background:#edf3fc;border:1px solid #d2dff0;border-radius:5px;padding:7px 12px}.shell-site-row .shell-site{border:0;padding:0;margin:0}
.shell-site{color:#243b59!important;-webkit-text-fill-color:#243b59!important;font-size:16px;font-weight:700;line-height:1.5;border-bottom:1px solid #d8e0ec;padding:0 0 10px;margin:0 0 12px}
.shell-page{display:flex;align-items:baseline;gap:20px;margin:0 0 12px}
.shell-page h1{font-size:27px!important;color:#111c2c!important;margin:0!important;line-height:1.35;font-weight:750!important;letter-spacing:-.6px}
.shell-page p{color:#415269!important;font-size:15px!important;margin:0;line-height:1.5}
h2,h3{color:#142234!important;font-size:19px!important}
[data-testid="stAppViewContainer"] p,[data-testid="stAppViewContainer"] label{color:#202c3d;font-size:15px}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] label p{color:#172b46!important;font-size:15px!important;font-weight:650!important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:#4b5c70!important;font-size:14px!important;line-height:1.6!important}
input,textarea,[data-baseweb="select"],[data-baseweb="select"] div{color:#172b46!important;font-size:16px!important}
input:disabled,textarea:disabled{color:#283c56!important;-webkit-text-fill-color:#283c56!important;opacity:1!important;background:#f2f5fa!important}
[data-testid="stSelectbox"] [data-baseweb="select"] *{color:#172b46!important;-webkit-text-fill-color:#172b46!important;opacity:1!important}
[role="listbox"],[data-baseweb="popover"],[role="option"]{background:#fff!important;color:#172b46!important}
[role="option"] *{color:#172b46!important;-webkit-text-fill-color:#172b46!important;opacity:1!important}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button{font-size:15px!important;font-weight:600;border-radius:4px}
[data-testid="stButton"] button[kind="primary"]{background:#2455a4;color:white}
[data-testid="stButton"] button[kind="primary"] p{color:white!important}
[data-testid="stPopover"] button{background:#fff!important;border:1px solid #aabbd2!important;min-height:44px}
[data-testid="stPopover"] button *,[data-testid="stPopoverBody"] button *{color:#172b46!important;-webkit-text-fill-color:#172b46!important;opacity:1!important;font-size:16px!important;font-weight:650!important}
[data-testid="stPopoverBody"]{background:#fff!important}
[data-testid="stMetric"]{background:#f4f6fa;border-radius:4px;padding:12px}
@media(max-width:700px){.shell-site-row{flex-wrap:wrap}.shell-user{margin-left:auto;font-size:14px}.block-container{padding:3.4rem .85rem 1.2rem!important}.shell-page{display:block}.shell-page h1{font-size:25px!important}.shell-page p{margin-top:5px}.shell-site{font-size:14px}}
/* Sidebar specificity must beat the general primary-button white text rule. */
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] p,
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] span,
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover p,
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:focus p,
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:active p{
color:#194c99!important;-webkit-text-fill-color:#194c99!important;opacity:1!important}
</style>''',unsafe_allow_html=True)


def choose(page):st.session_state['workspace_nav']=page

def select_building(value):
    st.session_state['clean-building']=value
    st.session_state['summary-building']=value


def sidebar(known):
    if st.session_state.get('workspace_nav') not in [x[0] for x in NAV]+['설정·백업']:st.session_state['workspace_nav']='종합현황'
    with st.sidebar:
        st.markdown('''<div class="shell-brand"><svg width="38" height="50" viewBox="0 0 38 50" fill="none"><path d="M3 47V25L12 19V47M16 47V8L25 2V47M29 47V16L36 20V47" stroke="#173c60" stroke-width="3"/></svg><div>개구부 안전관리<br>시스템<small>현장 안전관리</small></div></div>''',unsafe_allow_html=True)
        for name,icon in NAV:
            st.button(name,icon=icon,type='primary' if st.session_state.workspace_nav==name else 'secondary',key='nav-'+name,on_click=choose,args=(name,),width='stretch')
        st.button('휴대폰 간편 화면',icon=':material/smartphone:',on_click=set_view,args=('mobile',),width='stretch')
        st.divider()
        if st.session_state.get('clean-building') not in ['전체']+known:st.session_state['clean-building']='전체'
        building=st.session_state['clean-building']
        st.markdown('**동 선택**')
        with st.popover('전체 동' if building=='전체' else building,icon=':material/apartment:',width='stretch'):
            for value in ['전체']+known:
                st.button(('✓ ' if value==building else '')+('전체 동' if value=='전체' else value),key='building-choice-'+value,on_click=select_building,args=(value,),width='stretch')
        st.markdown('<div style="height:24px"></div>',unsafe_allow_html=True)
        st.button('설정·백업',icon=':material/settings:',type='primary' if st.session_state.workspace_nav=='설정·백업' else 'secondary',on_click=choose,args=('설정·백업',),width='stretch')
        profile=st.session_state.get('account_profile',{})
        st.caption(profile.get('display_name','')+' · '+('관리자' if profile.get('role')=='admin' else '팀원'))
        if st.button('로그아웃',icon=':material/logout:',width='stretch'):
            try:logout_current(accounts);st.rerun()
            except StoreError as exc:st.error(str(exc))
    return st.session_state.workspace_nav,building


def header(page,site):
    descriptions={'종합현황':'개구부와 안전점검 현황을 한눈에 확인합니다.','도면·개구부':'동별 도면과 개구부의 위치·종류·규격을 관리합니다.','안전점검':'점검 결과와 점검자·서명을 기록합니다.','사진·조치':'현장 사진과 조치 결과를 확인합니다.','보고서':'현황과 점검·조치 이력을 엑셀로 내려받습니다.','설정·백업':'현장 설정과 자료 백업을 관리합니다.'}
    profile=st.session_state.get('account_profile',{})
    display_name=str(profile.get('display_name') or '사용자')
    role='관리자' if profile.get('role')=='admin' else '팀원'
    st.markdown(f'<div class="shell-site-row"><div class="shell-site">{escape(site)}</div><div class="shell-user">{escape(display_name)} · {role}</div></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="shell-page"><h1>{escape(page)}</h1><p>{escape(descriptions.get(page,""))}</p></div>',unsafe_allow_html=True)

from account_auth import Accounts,AuthError
from account_ui import login_gate,account_page,clear_login,logout_current
from uuid import uuid4
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title='개구부 안전관리 시스템',page_icon=':material/health_and_safety:',layout='wide')
styles()
try:
    url=str(st.secrets.get('SUPABASE_URL',''))
    key=str(st.secrets.get('SUPABASE_SECRET_KEY',''))
    public_key=str(st.secrets.get('SUPABASE_PUBLISHABLE_KEY',''))
    app_url=str(st.secrets.get('APP_URL',''))
    if not all([url,key,public_key,app_url]):raise AuthError('개인 계정 설정이 필요합니다. 적용 안내의 Secrets 설정을 완료하세요.')
    accounts=Accounts(url,public_key,key,app_url)
except AuthError as exc:st.error(str(exc));st.stop()
except Exception:st.error('Streamlit Secrets 연결 설정을 확인하세요.');st.stop()
store,account_profile=login_gate(accounts)
st.session_state['account_profile']=account_profile
@st.fragment(run_every=60)
def check_date_change():
    current=datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    previous=st.session_state.get('inspection-ui-day',current)
    st.session_state['inspection-ui-day']=current
    if previous!=current:st.rerun()
check_date_change()

if not st.session_state.get('cloud_loaded'):
    try:
        remote=store.projects()
        st.session_state.projects={**remote,**st.session_state.get('projects',{})}
        st.session_state.cloud_loaded=True
    except Exception:st.error('저장소에 연결하지 못했습니다. 연결 설정을 확인해 주세요.');st.stop()
projects=st.session_state.projects
assign_names(projects)
try: buildings=store.list_buildings()
except StoreError as exc:st.error(str(exc));st.stop()
known=sorted({b['name'] for b in buildings}|{s['building'] for s in projects.values()})
if use_mobile():
    mobile_page(store,projects,known,account_profile,accounts)
    st.stop()
page,building=sidebar(known)
site=st.session_state.get('site_name',SITE)
date=st.session_state.get('report_date',datetime.now(ZoneInfo('Asia/Seoul')).date())
header(page,site)
menu={'종합현황':'대시보드','안전점검':'안전점검','사진·조치':'사진·조치','보고서':'보고용 엑셀','설정·백업':'설정·백업'}.get(page,'현황 보기')
if page=='도면·개구부':
    mode=st.radio('작업 화면',['도면·목록','등록·수정'],horizontal=True,key='drawing-workspace-mode',label_visibility='collapsed')
    menu='현황 보기' if mode=='도면·목록' else '등록·수정'

def read_source(state):
    cache=st.session_state.setdefault('drawing_cache',{})
    path=state.get('drawing_path')
    if not path:raise StoreError('원본 도면을 업로드해 주세요.')
    if path not in cache:
        cache.clear();cache[path]=store.download(state)
    return cache[path]

def save_state(state,data):
    try:
        assign_names(projects);store.save(state,data)
        st.session_state['save_notice']='저장 완료. 다음 접속에도 동별 메뉴에서 확인할 수 있습니다.'
        st.rerun()
    except StoreError as exc:st.error(str(exc))
    except Exception:st.error('저장하지 못했습니다. 화면의 입력 내용은 유지됩니다. 다시 시도해 주세요.')

if menu=='사진·조치':
    actions_page(store,projects,building);st.stop()
if menu=='보고용 엑셀':
    report_page(store,projects,building,site);st.stop()

if menu=='안전점검':
    inspections_page(store,projects,building)
    st.stop()

if menu in ['대시보드','현황 보기']:
    rows=simple_rows(projects,building)
    try: inspection_records=store.inspections()
    except StoreError:
        inspection_records=[]
        st.warning('점검 기록을 불러오지 못했습니다. 아래 점검 수치는 확인할 수 없습니다. 안전점검 메뉴에서 연결 상태를 확인하세요.')
        st.stop()
    for row in rows:
        item=Opening.model_validate(projects[row['_key']]['items'][row['_index']])
        row.update(status(item,inspection_records,datetime.now(ZoneInfo('Asia/Seoul')).date()))
    if menu=='대시보드':
        with st.container(border=True):
            a,b,c,d=st.columns([4,1.5,1.8,.75],vertical_alignment='bottom')
            a.text_input('현장명',value=site,disabled=True,key='summary-site')
            with b:
                st.markdown('**동 선택**')
                with st.popover('전체 동' if building=='전체' else building,icon=':material/apartment:',width='stretch'):
                    for value in ['전체']+known:
                        st.button(('✓ ' if value==building else '')+('전체 동' if value=='전체' else value),key='summary-choice-'+value,on_click=select_building,args=(value,),width='stretch')
            c.date_input('기준일',value=datetime.now(ZoneInfo('Asia/Seoul')).date(),disabled=True,key='summary-today')
            if d.button('조회',type='primary',width='stretch'):st.rerun()
        try:cases=[c for c in store.cases() if building=='전체' or c['building']==building]
        except StoreError:
            cases=None;st.info('사진·조치 집계는 action_migration.sql 실행 후 표시됩니다.')
        render_dashboard(rows,building,datetime.now(ZoneInfo('Asia/Seoul')).date(),known if building=='전체' else [building],cases)
        st.stop()
    cols=st.columns(3)
    cols[0].metric('전체 개구부',f'{len(rows)}개')
    cols[1].metric('확인 완료',f"{sum(r['확인 상태']=='확인 완료' for r in rows)}개")
    cols[2].metric('확인 필요',f"{sum(r['확인 상태']=='확인 필요' for r in rows)}개")
    st.write('')
    left,right=st.columns([3,1])
    with left:query=st.text_input('개구부 찾기',placeholder='명칭·종류·관리자 검색',label_visibility='collapsed')
    with right:
        if rows:st.download_button('엑셀 다운로드',xlsx_bytes(projects,site,date,None if building=='전체' else building,inspection_records),'개구부_현황.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',width='stretch')
    shown=[r for r in rows if not query or query.casefold() in ' '.join(str(v) for k,v in r.items() if not k.startswith('_')).casefold()]
    if not rows:
        st.info('저장한 개구부가 없습니다. 왼쪽 ‘등록·수정’에서 도면과 개구부를 등록해 주세요.')
    elif not shown:st.info('검색 결과가 없습니다.')
    else:
        st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if not k.startswith('_')} for r in shown]),hide_index=True,width='stretch')
        with st.expander('도면과 안전시설 상세 보기',expanded=False):
            selected=st.selectbox('확인할 개구부',range(len(shown)),format_func=lambda i:shown[i]['개구부 명칭'])
            row=shown[selected];state=projects[row['_key']];item=Opening.model_validate(state['items'][row['_index']])
            display_mode=st.radio('도면 표시',['선택한 개구부만','선택 강조','전체 표시'],horizontal=True)
            a,b=st.columns([1.25,1])
            with a:
                try:
                    im=drawing(store,state,projects,row['_index'],display_mode)
                    if im is not None:st.image(im,width='stretch')
                    else:st.info('원본 도면을 서버에 저장하면 위치를 볼 수 있습니다.')
                except StoreError as exc:st.error(str(exc))
            with b:detail(item)
    st.stop()

if menu=='설정·백업':
    account_page(accounts,account_profile)
    st.divider()
    st.subheader('동 관리')
    with st.form('building-add'):
        new_name=st.text_input('추가할 동',placeholder='예: 105동').strip()
        if st.form_submit_button('동 추가'):
            if not new_name:st.error('동 이름을 입력해 주세요.')
            else:
                try:store.building(new_name);st.rerun()
                except StoreError as exc:st.error(str(exc))
    with st.expander('현장명·엑셀 기준일'):
        st.text_input('현장명',value=site,key='site_name')
        st.date_input('기준일',value=date,key='report_date')
    with st.expander('도면 인식 설정'):
        st.text_input('Tesseract 실행 파일',value=os.getenv('TESSERACT_CMD','/usr/bin/tesseract'),key='ocr_path')
        st.selectbox('도면 언어',['eng','kor+eng'],key='ocr_lang')
    with st.expander('전체 자료 백업·복원'):
        st.caption('여러 동의 개구부 정보 백업입니다. 원본 도면 파일은 포함하지 않습니다. 도면 한 장용 JSON은 등록·수정 화면에서 가져오세요.')
        st.download_button('전체 자료 백업 다운로드',json.dumps({'schema':'building-register-v1','projects':projects},ensure_ascii=False,indent=2),'개구부_전체동_백업.json','application/json')
        backup=st.file_uploader('전체 동 백업 파일',type=['json'])
        if st.button('백업 가져오기',disabled=backup is None):
            try:
                obj=json.loads(backup.getvalue())
                if obj.get('schema')!='building-register-v1':raise ValueError('도면 한 장용 JSON입니다. 등록·수정에서 원본 도면을 열고 가져오세요.')
                restored={}
                for raw in obj['projects'].values():
                    s=dict(raw);s['items']=[Opening.model_validate(x).model_dump() for x in s['items']]
                    canonical=f"{s['building']}:{s['file_sha256']}:{s['page']-1}"
                    prior=projects.get(canonical,{})
                    for field in ['db_id','db_version','drawing_path']:s.pop(field,None)
                    s.update({field:prior[field] for field in ['db_id','db_version','drawing_path'] if field in prior})
                    s['version']=s.get('version',0)+1;restored[canonical]=s
                projects.update(restored);assign_names(projects)
                st.success('가져왔습니다. 영구 보관하려면 등록·수정에서 원본 도면을 열고 저장해 주세요.')
            except Exception as exc:st.error(f'가져오기 실패: {exc}')
    with st.expander('서버 자료 다시 불러오기'):
        confirm=st.checkbox('저장하지 않은 화면 수정 내용을 서버 자료로 바꿉니다.')
        if st.button('서버 자료 불러오기',disabled=not confirm):
            try:
                st.session_state.projects=store.projects();st.session_state.pop('drawing_cache',None);st.rerun()
            except StoreError as exc:st.error(str(exc))
    st.stop()

if building=='전체':
    st.info('왼쪽 ‘동 선택’에서 등록·수정할 동을 선택해 주세요. 새 동은 설정·백업에서 추가할 수 있습니다.');st.stop()
st.subheader(f'{building} 등록·수정')
choices={k:s for k,s in projects.items() if s['building']==building and s.get('drawing_path')}
source=st.radio('작업 선택',['저장한 도면 수정','새 도면 등록'] if choices else ['새 도면 등록'],horizontal=True,key='mode-'+building)
forced=None
if source=='저장한 도면 수정':
    selected=st.selectbox('도면 선택',list(choices),format_func=lambda k:f"{choices[k].get('drawing_title',choices[k]['filename'])} · {choices[k]['page']}페이지",key='edit-drawing-'+building)
    saved_state=choices[selected]
    try:data=read_source(saved_state)
    except StoreError as exc:st.error(str(exc));st.stop()
    filename=saved_state['filename'];forced=saved_state['page']-1
else:
    uploaded=st.file_uploader('도면 올리기',type=['png','jpg','jpeg','webp','pdf'],key='clean-upload-'+building)
    if uploaded is None:st.info('원본 도면 사진 또는 PDF를 올려주세요.');st.stop()
    data=uploaded.getvalue();filename=uploaded.name
if len(data)>30*1024*1024:st.error('30MB 이하 도면을 사용해 주세요.');st.stop()
file_hash=hashlib.sha256(data).hexdigest()
try:
    first,count,_=load_page(data,filename)
    page=forced if forced is not None else int(st.number_input('페이지',min_value=1,max_value=count,value=1,key='page-'+building+file_hash))-1 if count>1 else 0
    im,_,_=load_page(data,filename,page)
except Exception:st.error('도면을 열 수 없습니다. 파일 형식을 확인해 주세요.');st.stop()
page_id=f'{building}:{file_hash}:{page}'
state=projects.setdefault(page_id,{'building':building,'file_sha256':file_hash,'filename':filename,'page':page+1,'items':[],'notes':'','version':0})
if st.session_state.get('save_notice'):st.success(st.session_state.pop('save_notice'))
if st.session_state.get('revision_notice'):st.success(st.session_state.pop('revision_notice'))
revision_ui(store,projects,page_id,state)
with st.expander('기존 작업 가져오기 · 자동 인식'):
    st.caption('기존 JSON이 있으면 가져오기를 사용하세요. 자동 인식 결과는 종류·치수·위치를 확인해야 합니다.')
    imported=st.file_uploader('이 도면의 작업 JSON',type=['json'],key='page-json-'+page_id)
    replace=st.checkbox('현재 목록을 가져온 내용으로 교체',key='replace-'+page_id)
    if st.button('기존 작업 가져오기',disabled=imported is None or (bool(state['items']) and not replace)):
        try:
            obj=json.loads(imported.getvalue())
            if obj.get('file_sha256')!=file_hash or obj.get('page')!=page+1:raise ValueError('같은 원본 도면·페이지를 열어주세요.')
            if obj.get('building') and obj['building']!=building:raise ValueError('JSON에 저장된 동과 현재 동이 다릅니다.')
            state['items']=[Opening.model_validate(x).model_dump() for x in obj['openings']]
            state['notes']=obj.get('notes','');state['version']+=1;st.rerun()
        except Exception as exc:st.error(f'가져오기 실패: {exc}')
    if st.button('도면에서 개구부 찾기',disabled=bool(state['items'])):
        try:
            with st.spinner('도면을 읽는 중입니다…'):
                result,debug=detect_local(im,st.session_state.get('ocr_path','/usr/bin/tesseract'),st.session_state.get('ocr_lang','eng'))
            state.update(items=[x.model_dump() for x in result.openings],notes=result.notes,ocr_text=debug,version=state['version']+1);st.rerun()
        except Exception:st.error('자동 인식에 실패했습니다. 설정의 도면 언어·인식 경로를 확인해 주세요.')
    if state.get('ocr_text'):st.text(state['ocr_text'])
assign_names(projects)
labels={'active':'관리 중','management_name':'개구부 명칭','manager':'관리자','remark':'비고','name':'원본 명칭','kind':'종류','raw_size':'치수 원문','width_mm':'가로 (mm)','height_mm':'세로 (mm)','diameter_mm':'직경 (mm)','depth_mm':'높이·깊이 (mm)','x_pct':'위치 X (%)','y_pct':'위치 Y (%)','evidence':'인식 메모','reviewed':'확인 완료','label_x_pct':'이름표 X (%)','label_y_pct':'이름표 Y (%)'}
frame=pd.DataFrame(state['items'],columns=list(Opening.model_fields))
config={k:st.column_config.TextColumn(v) for k,v in labels.items()}
config['label_cover_width_pct']=None
config['active']=st.column_config.CheckboxColumn('관리 중',default=True)
config['opening_id']=None
config['inspection_weekdays']=None
config['kind']=st.column_config.SelectboxColumn('종류',options=TYPES,required=True)
config['reviewed']=st.column_config.CheckboxColumn('확인 완료',default=False)
for k in ['width_mm','height_mm','diameter_mm','depth_mm','x_pct','y_pct','label_x_pct','label_y_pct']:
    config[k]=st.column_config.NumberColumn(labels[k],min_value=0.,max_value=100. if k.endswith('pct') else None)
st.caption('치수는 mm입니다. 새 도면에서 없어진 개구부는 관리 중 체크를 해제하세요. 명칭·과거 점검 이력은 유지됩니다. 변경 내용 저장을 누르면 서버에 저장됩니다.')
with st.form('clean-edit-'+page_id):
    edited=st.data_editor(frame,column_config=config,column_order=['active','management_name','kind','width_mm','height_mm','diameter_mm','depth_mm','manager','reviewed','remark','name','raw_size','x_pct','y_pct','evidence','label_x_pct','label_y_pct'],disabled=['management_name'],num_rows='fixed',hide_index=True,width='stretch',key='clean-editor-'+page_id+'-'+str(state['version']))
    save=st.form_submit_button('변경 내용 저장',type='primary')
if save:
    try:
        state['items']=[x.model_dump() for x in normalize_rows(edited.to_dict('records'))];state['version']+=1
        save_state(state,data)
    except Exception:st.error('입력값을 확인해 주세요. 치수는 0 이상의 숫자 또는 빈칸으로 입력합니다.')
if st.button('개구부 추가'):
    state['items'].append(blank().model_dump());state['version']+=1;st.rerun()
items=[Opening.model_validate(x) for x in state['items']]
st.subheader('도면에서 위치 지정·누락 개구부 추가')
st.caption('이름표 위치 수정: 원본 영어 명칭의 왼쪽 위를 클릭해 관리 명칭을 덮어 표시하세요. 아래 규격은 가리지 않게 배치하세요. 원본 파일은 바뀌지 않습니다.')
action=st.radio('도면 작업',['누락 개구부 추가','개구부 위치 수정','이름표 위치 수정'],horizontal=True)
preview=annotate(im,items);preview.thumbnail((1400,1400))
selected=None
if action!='누락 개구부 추가':
    if items:selected=st.selectbox('대상 개구부',range(len(items)),format_func=lambda i:items[i].management_name,key='loc-'+page_id)
    else:st.info('먼저 개구부를 추가해 주세요.')
if action=='이름표 위치 수정' and selected is not None:
    st.caption('클릭 지점은 이름표의 왼쪽 위입니다. 폭을 늘리면 긴 영어 명칭도 가릴 수 있습니다.')
    cover_width=st.slider('이름표 배경 폭 (도면 너비 %)',0.0,40.0,float(items[selected].label_cover_width_pct or 0),0.5,key='cover-width-'+page_id+'-'+items[selected].opening_id)
    st.caption('0은 글자에 맞는 자동 폭입니다. 위치 저장 시 함께 저장됩니다.')
event=streamlit_image_coordinates(preview,key='map-'+page_id+'-'+str(state['version'])+'-'+action+'-'+str(selected))
if event:
    xp=round(max(0,min(100,event['x']/preview.width*100)),2)
    yp=round(max(0,min(100,event['y']/preview.height*100)),2)
    st.info(f'선택한 위치: X {xp:g}% / Y {yp:g}%')
    if action=='누락 개구부 추가':
        with st.form('manual-add-'+page_id):
            kind=st.selectbox('개구부 종류',TYPES)
            shape=st.radio('형태',['사각형','원형'],horizontal=True)
            st.caption('사각형은 가로·세로, 원형은 직경을 입력하세요. 모든 치수 단위는 mm입니다.')
            c1,c2,c3,c4=st.columns(4)
            width=c1.number_input('가로 (mm)',min_value=0.,value=None)
            height=c2.number_input('세로 (mm)',min_value=0.,value=None)
            diameter=c3.number_input('직경 (mm)',min_value=0.,value=None)
            depth=c4.number_input('수직 높이·깊이 (mm)',min_value=0.,value=None)
            original=st.text_input('도면 치수 원문 (선택)',placeholder='도면에 적힌 표기를 그대로 입력')
            checked=st.checkbox('종류·치수·위치를 확인했습니다')
            add=st.form_submit_button('이 위치에 개구부 추가·저장',type='primary')
        if add:
            valid=(width is not None and width>0 and height is not None and height>0) if shape=='사각형' else diameter is not None and diameter>0
            if kind=='확인 필요':st.error('개구부 종류를 선택해 주세요.')
            elif not valid:st.error('사각형은 가로·세로, 원형은 직경을 0보다 크게 입력해 주세요.')
            else:
                new=blank().model_dump()
                new.update(kind=kind,name='수동 등록',raw_size=original,width_mm=width if shape=='사각형' else None,height_mm=height if shape=='사각형' else None,diameter_mm=diameter if shape=='원형' else None,depth_mm=depth,x_pct=xp,y_pct=yp,reviewed=checked,evidence='사용자가 도면 클릭 후 종류·치수 입력')
                state['items'].append(Opening.model_validate(new).model_dump());state['version']+=1
                save_state(state,data)
    elif selected is not None:
        if st.button('선택한 위치 저장'):
            if action=='이름표 위치 수정':state['items'][selected].update(label_x_pct=xp,label_y_pct=yp,label_cover_width_pct=cover_width)
            else:state['items'][selected].update(x_pct=xp,y_pct=yp,reviewed=False)
            state['version']+=1;save_state(state,data)
if action=='이름표 위치 수정' and selected is not None and st.button('이름표 자동 배치로 복원'):
    state['items'][selected].update(label_x_pct=None,label_y_pct=None,label_cover_width_pct=None);state['version']+=1;save_state(state,data)
with st.expander('이 도면 백업·다운로드'):
    obj={'schema_version':2,'building':building,'file_sha256':file_hash,'filename':filename,'page':page+1,'notes':state['notes'],'openings':state['items']}
    st.download_button('작업 JSON 다운로드',json.dumps(obj,ensure_ascii=False,indent=2),'openings_p'+str(page+1)+'.json','application/json')
    st.download_button('표시 도면 다운로드',png_bytes(annotate(im,items)),'개구부_표시도면.png','image/png')
