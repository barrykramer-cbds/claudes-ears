#!/usr/bin/env python3
"""Claude's Ears - Temporal Segmentation
Rolling window analysis: transforms static portraits into movies."""

import numpy as np, librosa, json, sys, os, warnings
warnings.filterwarnings('ignore')

def temporal_segmentation(file_path, window_sec=15, hop_sec=5, sr=22050):
    print(f"Loading {os.path.basename(file_path)}...")
    y, sr = librosa.load(file_path, sr=sr, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    print(f"Duration: {duration:.1f}s | Window: {window_sec}s | Hop: {hop_sec}s")

    ws = int(window_sec * sr)
    hs = int(hop_sec * sr)
    pcs = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    cons_w = {0:1.0,7:0.9,5:0.85,4:0.8,3:0.75,8:0.7,9:0.7,2:0.5,10:0.5,6:0.3,1:0.2,11:0.2}

    snapshots = []
    pos, idx = 0, 0

    while pos + ws <= len(y):
        seg = y[pos:pos+ws]
        tc = (pos/sr + (pos+ws)/sr) / 2
        snap = {"seg": idx, "t_start": round(pos/sr,2), "t_end": round((pos+ws)/sr,2),
                "t_center": round(tc,2), "time": f"{int(tc//60)}:{int(tc%60):02d}"}

        # Energy
        rms = librosa.feature.rms(y=seg)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        snap["rms_mean"] = round(float(np.mean(rms_db)),2)
        snap["rms_p90"] = round(float(np.percentile(rms_db,90)),2)
        good = rms_db[rms_db > -60]
        snap["dyn_range"] = round(float(np.ptp(good)),2) if len(good)>1 else 0

        # Spectral
        snap["centroid"] = round(float(np.mean(librosa.feature.spectral_centroid(y=seg,sr=sr)[0])),1)

        # H/P
        yh, yp = librosa.effects.hpss(seg)
        he, pe = float(np.sum(yh**2)), float(np.sum(yp**2))
        snap["harm_pct"] = round(he/(he+pe+1e-10)*100,1)

        # Chroma / Key
        chroma = librosa.feature.chroma_cqt(y=seg, sr=sr)
        cm = chroma.mean(axis=1)
        snap["key"] = pcs[np.argmax(cm)]

        # Tension
        cdists = []
        for i in range(1, chroma.shape[1]):
            a, b = chroma[:,i-1], chroma[:,i]
            na, nb = np.linalg.norm(a), np.linalg.norm(b)
            if na>0 and nb>0: cdists.append(1-np.dot(a,b)/(na*nb))
        snap["tension"] = round(float(np.mean(cdists)),4) if cdists else 0

        # Consonance
        cscores = []
        for i in range(chroma.shape[1]):
            fr = chroma[:,i]
            if fr.max()>0:
                fr = fr/fr.max()
                s, tw = 0, 0
                for j in range(12):
                    for k in range(j+1,12):
                        iv = (k-j)%12
                        w = cons_w.get(iv,0.5)
                        s += w*fr[j]*fr[k]; tw += fr[j]*fr[k]
                if tw>0: cscores.append(s/tw)
        snap["consonance"] = round(float(np.mean(cscores)),4) if cscores else 0

        # Warmth
        S = np.abs(librosa.stft(seg))
        freqs = librosa.fft_frequencies(sr=sr)
        wm = (freqs>=200)&(freqs<=2000)
        we = float(np.mean(S[wm,:])) if wm.any() else 0
        snap["warmth"] = round(we/(float(np.mean(S))+1e-10),4)

        # Onsets
        ons = librosa.onset.onset_detect(y=seg, sr=sr)
        snap["onset_density"] = round(len(ons)/window_sec,2)

        # Tempo
        tempo, beats = librosa.beat.beat_track(y=seg, sr=sr)
        snap["tempo"] = round(float(np.atleast_1d(tempo)[0]),1)

        snapshots.append(snap)
        pos += hs; idx += 1

    print(f"Generated {len(snapshots)} segments")
    return snapshots

def narrative(snaps):
    if not snaps: return {}
    n = {}
    n["climax"] = {"time": max(snaps,key=lambda s:s["rms_p90"])["time"],
                   "db": max(snaps,key=lambda s:s["rms_p90"])["rms_p90"]}
    n["quietest"] = {"time": min(snaps,key=lambda s:s["rms_mean"])["time"],
                     "db": min(snaps,key=lambda s:s["rms_mean"])["rms_mean"]}
    n["peak_tension"] = {"time": max(snaps,key=lambda s:s["tension"])["time"],
                         "val": max(snaps,key=lambda s:s["tension"])["tension"]}

    # Transitions
    ec = [s["rms_p90"] for s in snaps]
    trans = []
    for i in range(1,len(ec)):
        d = ec[i]-ec[i-1]
        if abs(d)>3:
            trans.append({"time":snaps[i]["time"],"type":"BUILD" if d>0 else "DROP","db":round(d,1)})
    n["transitions"] = trans

    # Key changes
    kc = []
    for i in range(1,len(snaps)):
        if snaps[i]["key"]!=snaps[i-1]["key"]:
            kc.append({"time":snaps[i]["time"],"from":snaps[i-1]["key"],"to":snaps[i]["key"]})
    n["key_changes"] = kc

    # Arc
    t = len(snaps)//3
    e1 = np.mean([s["rms_p90"] for s in snaps[:t]])
    e2 = np.mean([s["rms_p90"] for s in snaps[t:2*t]])
    e3 = np.mean([s["rms_p90"] for s in snaps[2*t:]])
    t1 = np.mean([s["tension"] for s in snaps[:t]])
    t2 = np.mean([s["tension"] for s in snaps[t:2*t]])
    t3 = np.mean([s["tension"] for s in snaps[2*t:]])

    if e2>e1 and e2>e3: earc="peak in middle"
    elif e3>e2>e1: earc="continuous build"
    elif e1>e2>e3: earc="continuous decay"
    else: earc="complex"

    n["arc"] = {"energy":earc,"e_thirds":[round(e1,1),round(e2,1),round(e3,1)],
                "t_thirds":[round(t1,4),round(t2,4),round(t3,4)]}
    return n

def print_timeline(snaps, narr):
    print(f"\n{'='*70}")
    print("  TEMPORAL PERCEPTION TIMELINE")
    print(f"{'='*70}")

    print("\n  ENERGY (RMS P90):")
    for s in snaps:
        bl = max(0,int((s["rms_p90"]+20)*2))
        print(f"    {s['time']:>5s}  {'#'*min(bl,40):<40s}  {s['rms_p90']:>6.1f} dB")

    print("\n  TENSION:")
    for s in snaps:
        bl = int(s["tension"]*50)
        print(f"    {s['time']:>5s}  {'='*min(bl,40):<40s}  {s['tension']:.3f}")

    print("\n  WARMTH:")
    for s in snaps:
        bl = int(s["warmth"]*30)
        print(f"    {s['time']:>5s}  {'-'*min(bl,40):<40s}  {s['warmth']:.3f}")

    print(f"\n{'='*70}")
    print("  NARRATIVE")
    print(f"{'='*70}")
    print(f"  Energy arc: {narr.get('arc',{}).get('energy','?')}")
    print(f"  Climax: {narr.get('climax',{}).get('time','?')} ({narr.get('climax',{}).get('db','?')} dB)")
    print(f"  Quietest: {narr.get('quietest',{}).get('time','?')}")
    print(f"  Peak tension: {narr.get('peak_tension',{}).get('time','?')}")

    trans = narr.get("transitions",[])
    if trans:
        print("\n  STRUCTURAL MOMENTS:")
        for t in trans:
            arrow = "^" if t["type"]=="BUILD" else "v"
            print(f"    {arrow} {t['type']} at {t['time']} ({t['db']:+.1f} dB)")

    kc = narr.get("key_changes",[])
    if kc:
        print(f"\n  KEY SHIFTS ({len(kc)} total):")
        for k in kc[:15]:
            print(f"    {k['time']}: {k['from']} -> {k['to']}")
    print(f"{'='*70}")

if __name__ == "__main__":
    if len(sys.argv)<2: print("Usage: python temporal_segmentation.py <audio> [window] [hop]"); sys.exit(1)
    ws = int(sys.argv[2]) if len(sys.argv)>2 else 15
    hs = int(sys.argv[3]) if len(sys.argv)>3 else 5
    snaps = temporal_segmentation(sys.argv[1], ws, hs)
    narr = narrative(snaps)
    print_timeline(snaps, narr)
    out = sys.argv[1].rsplit('.',1)[0] + '_temporal.json'
    with open(out,'w') as f: json.dump({"snapshots":snaps,"narrative":narr},f,indent=2)
    print(f"\nSaved: {out}")
