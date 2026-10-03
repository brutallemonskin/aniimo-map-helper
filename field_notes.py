"""Explicit, local map observations. Never feed unreviewed notes into routing."""
import base64, copy, io, json, math, re, threading, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import os

class FieldNotes:
    LIMIT=300
    def __init__(self,root):
        self.root=Path(root);self.folder=self.root/'user-data'/'map-notes';self.lock=threading.RLock()
    def _read(self):
        p=self.folder/'records.json'
        if not p.exists():return []
        try:
            data=json.loads(p.read_text(encoding='utf8'))
            if not isinstance(data,list):raise ValueError()
            return data
        except (ValueError,OSError) as e:raise ValueError('本地记录无法读取，请保留 user-data 文件夹以便检查。') from e
    def _write(self,rows):
        self.folder.mkdir(parents=True,exist_ok=True)
        tmp=self.folder/'records.tmp';tmp.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8');tmp.replace(self.folder/'records.json')
    def _id(self,value):
        if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{32}',value):raise ValueError('无效记录编号')
        return value
    def list(self):
        with self.lock:return copy.deepcopy(self._read())
    def detail(self,ident):
        with self.lock:
            ident=self._id(ident);row=next((r for r in self._read() if r['id']==ident),None)
            if row is None:raise ValueError('记录已不存在，请刷新列表。')
            row=copy.deepcopy(row)
            if row.get('image'):
                row['screenshot']='data:image/jpeg;base64,'+base64.b64encode((self.folder/row['image']).read_bytes()).decode()
            return row
    def save(self,d):
        if not isinstance(d,dict):raise ValueError('无效记录')
        map_id=d.get('map')
        if not isinstance(map_id,str) or not re.fullmatch(r'(sanctum|egg-heist)[a-z0-9-]*',map_id):raise ValueError('无效地图')
        path=self.root/'data'/f'{map_id}.json'
        if not path.is_file():raise ValueError('地图不存在')
        atlas=json.loads(path.read_text(encoding='utf8'))
        def point(p):
            return isinstance(p,list) and len(p)==2 and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<atlas[k] for v,k in zip(p,('width','height')))
        if not point(d.get('position')):raise ValueError('请选择地图内的位置')
        kind=d.get('kind')
        if kind not in ('passage','point','monster','spawn'):raise ValueError('请选择记录类型')
        end=d.get('end') if kind=='passage' else None
        if kind=='passage' and (not point(end) or math.dist(d['position'],end)<4):raise ValueError('请在地图上选择通路的另一端')
        def string(key,limit):
            v=d.get(key,'')
            if not isinstance(v,str) or len(v)>limit:raise ValueError('记录文字过长或格式错误')
            return v.strip()
        subject=string('subject',100);note=string('note',2000)
        if kind=='monster' and not subject:raise ValueError('请填写怪物名称')
        mode=d.get('mode','unknown');difficulty=d.get('difficulty','unknown');rank=d.get('rank','unknown');passage=d.get('passage','unknown')
        if mode not in ('unknown','normal','team') or difficulty not in ('unknown','beginner','hard','nightmare','chaos'):raise ValueError('无效模式或难度')
        if rank not in ('unknown','normal','elite','alpha','boss') or passage not in ('unknown','walk','stairs','jump','oneway','blocked'):raise ValueError('无效实测类型')
        image_time=string('image_time',80) if d.get('screenshot') else None
        image_data=None
        if d.get('screenshot'):
            raw=d['screenshot']
            if not isinstance(raw,str) or not raw.startswith('data:image/jpeg;base64,') or len(raw)>750000:raise ValueError('截图过大，请重新附上当前画面')
            try:
                image_data=base64.b64decode(raw.split(',',1)[1],validate=True)
                with Image.open(io.BytesIO(image_data)) as im:
                    if im.format!='JPEG' or not (0<im.width<=1600 and 0<im.height<=1600):raise ValueError()
                    im.verify()
            except Exception as e:raise ValueError('截图无效') from e
        with self.lock:
            rows=self._read();ident=self._id(d['id']) if d.get('id') else uuid.uuid4().hex
            old=next((r for r in rows if r['id']==ident),None)
            if d.get('id') and old is None:raise ValueError('记录已被删除，请重新创建。')
            if old and d.get('revision')!=old['revision']:raise ValueError('记录已被其他页面更新，请关闭后重新编辑。')
            if not old and len(rows)>=self.LIMIT:raise ValueError('本地记录已满，请先导出并删除旧记录。')
            now=datetime.now(timezone.utc).isoformat(timespec='seconds')
            row=dict(id=ident,map=map_id,map_name=atlas['name'],kind=kind,position=d['position'],end=end,subject=subject,note=note,mode=mode,difficulty=difficulty,rank=rank,passage=passage,created=old['created'] if old else now,updated=now,revision=old['revision']+1 if old else 1,status='unverified',image=old.get('image') if old else None)
            row['image_time']=old.get('image_time') if old else None
            if d.get('remove_image'):row['image']=None;row['image_time']=None
            new_image=None
            if image_data:
                if sum(p.stat().st_size for p in self.folder.glob('*.jpg'))+len(image_data)>50_000_000:raise ValueError('截图空间已满，请先导出并删除旧记录。')
                self.folder.mkdir(parents=True,exist_ok=True)
                new_image=self.folder/(uuid.uuid4().hex+'.jpg');new_image.write_bytes(image_data)
                row['image']=new_image.name;row['image_time']=image_time or now
            updated=[r for r in rows if r['id']!=ident]+[row]
            try:self._write(updated)
            except Exception:
                if new_image:new_image.unlink(missing_ok=True)
                raise
            if old and old.get('image') and old['image']!=row['image']:(self.folder/old['image']).unlink(missing_ok=True)
            return row
    def delete(self,ident,revision):
        with self.lock:
            ident=self._id(ident);rows=self._read();old=next((r for r in rows if r['id']==ident),None)
            if old and old['revision']!=revision:raise ValueError('记录已更新，请刷新列表后再删除。')
            self._write([r for r in rows if r['id']!=ident])
            if old and old.get('image'):(self.folder/old['image']).unlink(missing_ok=True)
            return {'deleted':True}
    def _map_overview(self,map_id,rows):
        atlas=json.loads((self.root/'data'/f'{map_id}.json').read_text(encoding='utf8'))
        image_path=self.root/atlas.get('image','').lstrip('/')
        if not image_path.is_file():return None
        with Image.open(image_path) as source:
            im=source.convert('RGB');im.thumbnail((1600,1600))
        sx=im.width/atlas['width'];sy=im.height/atlas['height']
        page=Image.new('RGB',(im.width,im.height+80),'#10212a');page.paste(im,(0,80));draw=ImageDraw.Draw(page)
        fonts=[Path(os.environ.get('WINDIR',r'C:\Windows'))/'Fonts/msyh.ttc',Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
        font=next((ImageFont.truetype(str(p),20) for p in fonts if p.is_file()),ImageFont.load_default())
        draw.text((16,10),atlas['name']+' · 玩家纠错与实测',font=font,fill='#b9fff7')
        draw.text((16,42),'待核实 · 编号对应实测记录.txt · 不代表官方点位',font=font,fill='#c5d5dd')
        names={'point':'纠错','passage':'通路','monster':'怪物','spawn':'刷新'}
        used=[]
        for r in rows:
            x,y=r['position'][0]*sx,80+r['position'][1]*sy
            if r.get('end'):
                ex,ey=r['end'][0]*sx,80+r['end'][1]*sy;draw.line((x,y,ex,ey),fill='#58dacf',width=4)
                draw.ellipse((ex-5,ey-5,ex+5,ey+5),fill='#58dacf')
            original_y=y
            for n in range(1,301):
                if all(math.hypot(x-px,y-py)>=40 for px,py in used):break
                y=original_y+math.ceil(n/2)*44*(1 if n%2 else -1)
            used.append((x,y))
            if y!=original_y:draw.line((x,original_y,x,y),fill='#58dacf',width=2)
            draw.polygon([(x,y-17),(x+17,y),(x,y+17),(x-17,y)],fill='#12312f',outline='#58dacf',width=3)
            number=str(r['marker_number']);draw.text((x,y),number,font=font,fill='#b9fff7',anchor='mm')
            label=names[r['kind']]+' #'+number;box=draw.textbbox((0,0),label,font=font);width=box[2]-box[0]+12
            tx=min(max(0,x+24),page.width-width);ty=min(max(80,y-17),page.height-34)
            draw.rectangle((tx,ty,tx+width,ty+32),fill='#12312f');draw.text((tx+6,ty+2),label,font=font,fill='#b9fff7')
        output=io.BytesIO();page.save(output,format='PNG');return output.getvalue()
    def export(self,map_id=None):
        with self.lock:
            rows=copy.deepcopy([r for r in reversed(self._read()) if map_id is None or r['map']==map_id])
            rows.sort(key=lambda r:r['created'],reverse=True)
            if not rows:raise ValueError('没有可导出的记录')
            output=io.BytesIO();kinds={'passage':'通路纠错','point':'点位纠错','monster':'怪物实测','spawn':'刷新记录'}
            labels={'unknown':'未知','normal':'普通','team':'小队','beginner':'初级','hard':'困难','nightmare':'噩梦','chaos':'混沌','elite':'精英','alpha':'头目','boss':'首领 / Boss','walk':'普通通路','stairs':'楼梯','jump':'跳跃','oneway':'单向落差（起点到终点）','blocked':'不通'}
            lines=['伊莫地图助手 · 玩家实测记录','全部为未经审核的玩家记录；单次出现不是刷新概率。','坐标为地图底图像素，通路方向为起点 → 终点。','截图仅包含玩家主动附上的画面。','']
            with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
                grouped={}
                for r in rows:
                    group=grouped.setdefault(r['map'],[]);group.append(r);r['marker_number']=len(group)
                for ident,group in grouped.items():
                    overview=self._map_overview(ident,group)
                    if overview:
                        filename=f'maps/{ident}.png';z.writestr(filename,overview)
                        for r in group:r['map_overview']=filename
                    else:lines.append(f'{ident}：底图暂不可用，已保留文字和坐标记录。')
                for r in rows:
                    lines.extend([f"{r['map_name']} · #{r['marker_number']} · {kinds[r['kind']]} · {r['created']}",f"标注地图：{r.get('map_overview') or '无'}",f"位置：{r['position']}"+(f" → {r['end']}" if r['end'] else ''),f"模式：{labels[r['mode']]}；难度：{labels[r['difficulty']]}",f"名称：{r['subject']}；怪物级别：{labels[r['rank']]}；通路：{labels[r['passage']]}",r['note'],f"截图：{r.get('image') or '未附图'}",''])
                    if r.get('image'):z.write(self.folder/r['image'],'screenshots/'+r['image'])
                z.writestr('records.json',json.dumps({'schema':1,'records':rows},ensure_ascii=False,indent=2))
                z.writestr('实测记录.txt','\n'.join(lines).encode('utf-8-sig'))
            return output.getvalue()
