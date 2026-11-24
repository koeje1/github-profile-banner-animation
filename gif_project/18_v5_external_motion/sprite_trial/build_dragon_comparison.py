"""Decode original Mir dragon stages and compare their authored flight cycles."""
from pathlib import Path
from PIL import Image,ImageDraw
import base64,json,hashlib

ROOT=Path(__file__).resolve().parent
stages=[2200,2211,2214,2217]
all_frames={}
summary={}
sheet=Image.new('RGB',(1488,816),'#e3e6eb')
d=ImageDraw.Draw(sheet)
for row,stage in enumerate(stages):
    folder=ROOT/f'mir-dragon{stage}'
    frames=[]
    metadata=[]
    for i in range(6):
        src=json.loads((folder/f'source-{i}.json').read_text(encoding='utf-8-sig'))
        origin=json.loads((folder/f'origin-{i}.json').read_text(encoding='utf-8-sig'))['value']
        delay=json.loads((folder/f'delay-{i}.json').read_text(encoding='utf-8-sig'))['value']
        rawpath=folder/f'frame-{i}.png'
        rawpath.write_bytes(base64.b64decode(src['value']))
        raw=Image.open(rawpath).convert('RGBA')
        aligned=Image.new('RGBA',(320,240))
        aligned.alpha_composite(raw,(160-origin['x'],170-origin['y']))
        aligned.save(folder/f'aligned-{i}.png')
        frames.append(aligned)
        metadata.append(dict(index=i,file=f'aligned-{i}.png',raw_file=f'frame-{i}.png',raw_size=raw.size,
                             origin=[origin['x'],origin['y']],aligned_origin=[160,170],delay_ms=delay,
                             opaque_bottom_relative_to_origin=raw.getbbox()[3]-origin['y'],
                             sha256=hashlib.sha256(raw.tobytes()).hexdigest(),
                             source=f'https://maplestory.io/api/wz/GMS/255/Skill/Dragon/{stage}.img/move/{i}'))
        x=i*248
        d.text((x+10,row*204+10),f'Dragon {stage} / {i} / {delay}ms',fill='#263444')
        # All stages displayed at 1x native pixel size on the same origin.
        sheet.paste(raw,(x+124-origin['x'],row*204+180-origin['y']),raw)
        d.line((x+5,row*204+180,x+243,row*204+180),fill='#bdc3ce')
        d.text((x+10,row*204+186),f'origin {origin["x"]},{origin["y"]}',fill='#465164')
    assert len({m['sha256'] for m in metadata})==6
    record=dict(stage=stage,animation='move',motion='Original dragon flight/hover cycle, not quadruped ground walking.',
                original_facing='left',aligned_canvas=[320,240],aligned_origin=[160,170],
                mirrored_facing='right',mirrored_origin=[160,170],cycle_ms=sum(m['delay_ms'] for m in metadata),
                frames=metadata)
    (folder/'metadata.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    all_frames[stage]=frames
    summary[stage]=record
sheet.save(ROOT/'mir-stage-comparison.png')

selected=all_frames[2211]
evan=[Image.open(ROOT/f'evan/aligned-{i}.png').convert('RGBA') for i in range(4)]
out=[]
transparent=[]
for ms in range(0,720,30):
    layer=Image.new('RGBA',(800,350))
    for source,anchor,target in [(selected[(ms//120)%6],(160,170),(265,277)),(evan[(ms//180)%4],(81,96),(600,277))]:
        # Pixel-boundary origins transform to width - origin under horizontal flip.
        ax=source.width-anchor[0]
        sprite=source.transpose(Image.Transpose.FLIP_LEFT_RIGHT).resize((source.width*2,source.height*2),Image.Resampling.NEAREST)
        layer.alpha_composite(sprite,(target[0]-ax*2,target[1]-anchor[1]*2))
    bg=Image.new('RGBA',layer.size,'#e3e6eb');draw=ImageDraw.Draw(bg)
    for y in range(0,350,16):
        for x in range(0,800,16):
            if(x//16+y//16)%2:draw.rectangle((x,y,x+15,y+15),fill='#dbe0e8')
    draw.text((16,16),'SELECTED: ORIGINAL EVAN WALK + MIR 2211 FLIGHT / NATIVE 720 ms LOOP',fill='#263444')
    draw.line((16,278,784,278),fill='#b5bdc9')
    bg.alpha_composite(layer)
    transparent.append(layer)
    out.append(bg.convert('RGB'))
atlas=Image.new('RGB',(800*6,350))
for i in range(6):atlas.paste(out[i*4],(i*800,0))
pal=atlas.quantize(colors=255)
q=[f.quantize(palette=pal,dither=Image.Dither.NONE) for f in out]
q[0].save(ROOT/'selected-motion-test.gif',save_all=True,append_images=q[1:],duration=30,loop=0,disposal=2,optimize=False)
out[0].save(ROOT/'selected-motion-poster.png')
transparent[0].save(ROOT/'selected-motion-transparent-poster.png')

selection=dict(chosen_stage=2211,reason='Closest young-dragon silhouette; no adult horns, aura or oversized wings. Its original flight cycle is a better fit than imposing a fabricated ground walk.',
               evan=dict(folder='evan',files='aligned-{0..3}.png',canvas=[128,128],left_facing_anchor=[81,96],right_facing_anchor=[47,96],delay_ms=180,cycle_ms=720),
               mir=dict(folder='mir-dragon2211',files='aligned-{0..5}.png',canvas=[320,240],left_facing_anchor=[160,170],right_facing_anchor=[160,170],delay_ms=120,cycle_ms=720),
               alignment_note='Mir anchor is the exact original WZ origin, which sits below his visible feet. This is intentional flight elevation. Evan anchor x=81 is a chosen display reference inside the source-GIF registration; its relative alignment between frames is source-derived.',
               rights='NEXON copyrighted game sprites, freely accessible via MapleStory.IO. Not CC0 or public domain.')
(ROOT/'selected-motion.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
print(json.dumps({stage:{'cycle_ms':m['cycle_ms'],'hover_bottom_offsets':[f['opaque_bottom_relative_to_origin'] for f in m['frames']]} for stage,m in summary.items()},indent=2))
