"""Conservative atlas-only route hints. Unknown terrain is never bridged."""
from pathlib import Path
from collections import OrderedDict
import heapq, json, math, re, threading
import cv2
import numpy as np
from image_io import read_image


class RoutePlanner:
    STEP=4
    def __init__(self,root):
        self.root=Path(root);self.cache=OrderedDict();self.tour_cache=OrderedDict();self.lock=threading.Lock()

    @staticmethod
    def floor_grid(image):
        # Bright neutral floor only; preserve dark walls and unknown areas.
        hsv=cv2.cvtColor(image[:,:,:3],cv2.COLOR_BGR2HSV)
        floor=((hsv[:,:,2]>=135)&(hsv[:,:,1]<=65)).astype(np.uint8)
        if image.shape[2]==4:floor[image[:,:,3]<200]=0
        floor=cv2.erode(floor,np.ones((3,3),np.uint8))
        h,w=floor.shape;s=RoutePlanner.STEP
        return floor[:h-h%s,:w-w%s].reshape(h//s,s,w//s,s).min(axis=(1,3)).astype(bool)

    def grid(self,map_id):
        if map_id not in self.cache:
            data=json.loads((self.root/'data'/f'{map_id}.json').read_text(encoding='utf8'))
            im=read_image(self.root/data['image'].lstrip('/'),cv2.IMREAD_UNCHANGED)
            if im is None:raise ValueError('地图底图不可用')
            self.cache[map_id]=self.floor_grid(im)
            if len(self.cache)>4:self.cache.popitem(last=False)
        self.cache.move_to_end(map_id)
        return self.cache[map_id]

    @staticmethod
    def snap(grid,p):
        s=RoutePlanner.STEP;cx,cy=int(p[0]/s),int(p[1]/s);h,w=grid.shape
        if not(0<=cx<w and 0<=cy<h):return None
        # Limit correction to icon/registration uncertainty (24 atlas pixels).
        x0,x1=max(0,cx-6),min(w,cx+7);y0,y1=max(0,cy-6),min(h,cy+7)
        yy,xx=np.where(grid[y0:y1,x0:x1]);xx=xx+x0;yy=yy+y0
        if not len(xx):return None
        distance=(xx*s+s/2-p[0])**2+(yy*s+s/2-p[1])**2;i=int(np.argmin(distance))
        return (int(xx[i]),int(yy[i])) if distance[i]<=24**2 else None

    def plan(self,payload):
        if not isinstance(payload,dict):raise ValueError('无效路线请求')
        map_id=payload.get('map');start=payload.get('position');targets=payload.get('targets')
        def point(p):return isinstance(p,list) and len(p)==2 and all(type(v) in (int,float) and math.isfinite(v) and 0<=v<10000 for v in p)
        if not isinstance(map_id,str) or not re.fullmatch(r'sanctum-[a-z0-9-]+',map_id):raise ValueError('参考路线暂仅支持地宫')
        if not (self.root/'data'/f'{map_id}.json').is_file():raise ValueError('未知地图')
        if not point(start) or not isinstance(targets,list) or not 1<=len(targets)<=32:raise ValueError('无效路线起点或目标')
        for t in targets:
            if not isinstance(t,dict) or not point(t.get('position')) or not isinstance(t.get('key'),str) or len(t['key'])>256:raise ValueError('无效路线目标')
        with self.lock:
            if payload.get('mode')=='egg-tour':
                return self.tour(self.grid(map_id),start,targets,map_id)
            return self.search(self.grid(map_id),start,targets)

    @staticmethod
    def paths_from(grid,source,goals):
        """One Dijkstra pass for all stops; never cut a diagonal through a wall."""
        pending=set(goals);found={};queue=[(0,source)];cost={source:0};previous={};h,w=grid.shape
        while queue and pending:
            distance,p=heapq.heappop(queue)
            if distance!=cost[p]:continue
            if p in pending:
                path=[p]
                while path[-1]!=source:path.append(previous[path[-1]])
                path.reverse();compact=[path[0]]
                for i in range(1,len(path)-1):
                    a,b,c=path[i-1:i+2]
                    if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):compact.append(b)
                if len(path)>1:compact.append(path[-1])
                found[p]=(distance,compact);pending.remove(p)
            x,y=p
            for dx,dy in ((0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
                nx,ny=x+dx,y+dy
                if not(0<=nx<w and 0<=ny<h) or not grid[ny,nx]:continue
                if dx and dy and (not grid[y,nx] or not grid[ny,x]):continue
                q=(nx,ny);d=distance+(math.sqrt(2) if dx and dy else 1)
                if d<cost.get(q,float('inf')):cost[q]=d;previous[q]=p;heapq.heappush(queue,(d,q))
        return found

    @staticmethod
    def tour_order(matrix):
        """Shortest open tour from vertex 0; exact DP for all current atlas nest counts."""
        n=len(matrix)-1
        if not n:return [],True
        if n<=12:
            dp={};parent={}
            for j in range(n):dp[(1<<j,j)]=matrix[0][j+1]
            for mask in range(1,1<<n):
                for j in range(n):
                    value=dp.get((mask,j))
                    if value is None:continue
                    for k in range(n):
                        if mask&(1<<k):continue
                        key=(mask|(1<<k),k);new=value+matrix[j+1][k+1]
                        if new<dp.get(key,float('inf')):dp[key]=new;parent[key]=j
            mask=(1<<n)-1;j=min(range(n),key=lambda j:dp[(mask,j)]);order=[]
            while mask:
                order.append(j+1);old=j;j=parent.get((mask,j),-1);mask^=1<<old
            return order[::-1],True
        # Bound memory for future maps with many more nests. Explicitly label approximate.
        remaining=set(range(1,n+1));order=[];last=0
        while remaining:
            last=min(remaining,key=lambda j:(matrix[last][j],j));order.append(last);remaining.remove(last)
        def length(seq):return sum(matrix[a][b] for a,b in zip([0]+seq,seq))
        for _ in range(n):
            before=length(order);best=order
            for i in range(n):
                for j in range(i+1,n):
                    candidate=order[:i]+order[i:j+1][::-1]+order[j+1:]
                    if length(candidate)<length(best)-1e-9:best=candidate
            order=best
            if length(order)>=before-1e-9:break
        return order,False

    def tour(self,grid,start,targets,map_id=None):
        source=self.snap(grid,start);groups={};unreachable=[]
        for t in targets:
            p=self.snap(grid,t['position'])
            if p is None:unreachable.append(t['key'])
            else:groups.setdefault(p,[]).append(t['key'])
        if source is None:
            return {'status':'unavailable','path':[],'stops':[],'unreachable':[t['key'] for t in targets],
                    'reason':'当前位置无法接入底图通道，请移动后重新规划。'}
        first=self.paths_from(grid,source,groups)
        for p in list(groups):
            if p not in first:unreachable.extend(groups.pop(p))
        nodes=tuple(sorted(groups));cache_key=(map_id,nodes)
        edges=self.tour_cache.get(cache_key) if map_id else None
        if edges is None:
            edges={}
            for i,p in enumerate(nodes):
                for q,(distance,path) in self.paths_from(grid,p,nodes[i+1:]).items():
                    edges[p,q]=(distance,path);edges[q,p]=(distance,path[::-1])
            if map_id:
                self.tour_cache[cache_key]=edges
                if len(self.tour_cache)>4:self.tour_cache.popitem(last=False)
        elif map_id:self.tour_cache.move_to_end(cache_key)
        matrix=[[0]*(len(nodes)+1) for _ in range(len(nodes)+1)]
        for i,p in enumerate(nodes,1):
            matrix[0][i]=matrix[i][0]=first[p][0]
            for j,q in enumerate(nodes,1):
                if i!=j:matrix[i][j]=edges[p,q][0]
        order,exact=self.tour_order(matrix);path=[];stops=[];last=None;distance=0
        for i in order:
            p=nodes[i-1];length,segment=first[p] if last is None else edges[last,p]
            path.extend(segment if not path else segment[1:]);distance+=length;last=p
            for key in groups[p]:stops.append({'key':key,'position':[p[0]*4+2,p[1]*4+2]})
        return {'status':'ok' if stops else 'unavailable','path':[[x*4+2,y*4+2] for x,y in path],
                'target':stops[0]['key'] if stops else None,'stops':stops,'unreachable':unreachable,
                'length':round(distance*4),'exact':exact,'reason':'底图参考路线 · 门锁和高低差需游戏内核对'}

    def search(self,grid,start,targets):
        source=self.snap(grid,start);goals={}
        for target in targets:
            p=self.snap(grid,target['position'])
            if p is not None:goals.setdefault(p,target['key'])
        missing={'status':'unavailable','path':[],'reason':'底图暂不能确认连通路线，请在游戏内核对。'}
        if source is None or not goals:return missing
        queue=[(0,source)];cost={source:0};previous={};h,w=grid.shape;visited=0
        while queue and visited<80000:
            distance,p=heapq.heappop(queue)
            if distance!=cost[p]:continue
            visited+=1
            if p in goals:
                path=[p]
                while path[-1]!=source:path.append(previous[path[-1]])
                path.reverse()
                # Remove collinear nodes only, never cut across a corner.
                compact=[path[0]]
                for i in range(1,len(path)-1):
                    a,b,c=path[i-1:i+2]
                    if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):compact.append(b)
                if len(path)>1:compact.append(path[-1])
                return {'status':'ok','target':goals[p],'path':[[x*self.STEP+2,y*self.STEP+2] for x,y in compact],
                        'length':round(distance*self.STEP),'reason':'底图参考路线 · 门锁和高低差需游戏内核对'}
            x,y=p
            for dx,dy in ((0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)):
                nx,ny=x+dx,y+dy
                if not(0<=nx<w and 0<=ny<h) or not grid[ny,nx]:continue
                if dx and dy and (not grid[y,nx] or not grid[ny,x]):continue
                q=(nx,ny);d=distance+(math.sqrt(2) if dx and dy else 1)
                if d<cost.get(q,float('inf')):cost[q]=d;previous[q]=p;heapq.heappush(queue,(d,q))
        return missing
