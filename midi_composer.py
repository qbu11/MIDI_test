import mido
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import threading
import time
import random
import os
from PIL import Image, ImageTk
import rtmidi

class MidiComposer:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDI 作曲工具")
        self.root.geometry("1000x600")
        self.root.configure(bg="#f0f0f0")
        
        # MIDI参数
        self.tempo = 120  # BPM
        self.time_signature = (4, 4)  # 4/4拍
        self.scale = [0, 2, 4, 5, 7, 9, 11]  # C大调音阶
        self.octave_range = (3, 6)  # 音符范围: C3 到 B6
        self.track_notes = []  # 存储生成的音符
        self.playing = False
        self.current_position = 0
        
        # 乐器设置
        self.instruments = {
            "钢琴": 0,
            "小提琴": 40,
            "大提琴": 42,
            "定音鼓": 47,
            "三角铁": 80,
            "弦乐合奏": 48
        }
        
        # 拉赫玛尼诺夫第二主题的音符序列（简化版）
        self.rachmaninoff_theme = [
            # 第一句
            {'note': 60, 'duration': 1.0},  # C4
            {'note': 64, 'duration': 0.5},  # E4
            {'note': 67, 'duration': 0.5},  # G4
            {'note': 72, 'duration': 1.0},  # C5
            {'note': 67, 'duration': 0.5},  # G4
            {'note': 64, 'duration': 0.5},  # E4
            # 第二句
            {'note': 60, 'duration': 1.0},  # C4
            {'note': 64, 'duration': 0.5},  # E4
            {'note': 67, 'duration': 0.5},  # G4
            {'note': 72, 'duration': 1.0},  # C5
            {'note': 67, 'duration': 0.5},  # G4
            {'note': 64, 'duration': 0.5},  # E4
        ]
        
        # MIDI输出
        self.midi_out = None
        self.try_initialize_midi()
        
        # 创建界面
        self.create_widgets()
        
        # 退出时清理资源
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def try_initialize_midi(self):
        """尝试初始化MIDI输出设备"""
        try:
            self.midi_out = rtmidi.MidiOut()
            available_ports = self.midi_out.get_ports()
            
            # 如果有可用的MIDI设备，连接到第一个
            if available_ports:
                self.midi_out.open_port(0)
                print(f"已连接到MIDI输出设备: {available_ports[0]}")
            else:
                # 如果没有可用的MIDI设备，打开虚拟端口
                self.midi_out.open_virtual_port("MIDI作曲工具输出")
                print("已创建虚拟MIDI输出端口")
                
        except Exception as e:
            print(f"MIDI初始化错误: {e}")
            self.midi_out = None
        
    def create_widgets(self):
        # 顶部控制区
        control_frame = tk.Frame(self.root, bg="#e0e0e0", padx=10, pady=10)
        control_frame.pack(fill=tk.X)
        
        # 速度控制
        tk.Label(control_frame, text="速度 (BPM):", bg="#e0e0e0").grid(row=0, column=0, padx=5, pady=5)
        self.tempo_var = tk.IntVar(value=self.tempo)
        tempo_spinner = tk.Spinbox(control_frame, from_=40, to=240, textvariable=self.tempo_var, width=5)
        tempo_spinner.grid(row=0, column=1, padx=5, pady=5)
        
        # 小节数控制
        tk.Label(control_frame, text="小节数:", bg="#e0e0e0").grid(row=0, column=2, padx=5, pady=5)
        self.bars_var = tk.IntVar(value=4)
        bars_spinner = tk.Spinbox(control_frame, from_=1, to=16, textvariable=self.bars_var, width=5)
        bars_spinner.grid(row=0, column=3, padx=5, pady=5)
        
        # 音阶选择
        tk.Label(control_frame, text="音阶:", bg="#e0e0e0").grid(row=0, column=4, padx=5, pady=5)
        self.scale_var = tk.StringVar(value="C大调")
        scales = ["C大调", "A小调", "G大调", "E小调", "F大调", "D小调"]
        scale_menu = ttk.Combobox(control_frame, textvariable=self.scale_var, values=scales, width=10)
        scale_menu.grid(row=0, column=5, padx=5, pady=5)
        
        # 生成模式选择
        tk.Label(control_frame, text="生成模式:", bg="#e0e0e0").grid(row=0, column=6, padx=5, pady=5)
        self.mode_var = tk.StringVar(value="拉赫玛尼诺夫风格")
        modes = ["拉赫玛尼诺夫风格", "完全随机"]
        mode_menu = ttk.Combobox(control_frame, textvariable=self.mode_var, values=modes, width=15)
        mode_menu.grid(row=0, column=7, padx=5, pady=5)
        
        # 乐器选择
        tk.Label(control_frame, text="乐器:", bg="#e0e0e0").grid(row=0, column=8, padx=5, pady=5)
        self.instrument_var = tk.StringVar(value="钢琴")
        instrument_menu = ttk.Combobox(control_frame, textvariable=self.instrument_var, 
                                     values=list(self.instruments.keys()), width=10)
        instrument_menu.grid(row=0, column=9, padx=5, pady=5)
        
        # 按钮区
        button_frame = tk.Frame(control_frame, bg="#e0e0e0")
        button_frame.grid(row=0, column=10, padx=20, pady=5, columnspan=3)
        
        generate_btn = tk.Button(button_frame, text="生成音乐", command=self.generate_music, 
                                 bg="#4CAF50", fg="white", padx=10)
        generate_btn.pack(side=tk.LEFT, padx=5)
        
        play_btn = tk.Button(button_frame, text="播放", command=self.play_music, 
                             bg="#2196F3", fg="white", padx=10)
        play_btn.pack(side=tk.LEFT, padx=5)
        
        stop_btn = tk.Button(button_frame, text="停止", command=self.stop_music, 
                            bg="#f44336", fg="white", padx=10)
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = tk.Button(button_frame, text="保存MIDI", command=self.save_midi, 
                             bg="#9C27B0", fg="white", padx=10)
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # 音符显示区域
        self.canvas_frame = tk.Frame(self.root, bg="white")
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="white", highlightthickness=1, 
                               highlightbackground="#cccccc")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 播放指示器
        self.position_line = None
        
        # 状态栏
        self.status_var = tk.StringVar(value="准备就绪")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def get_scale_notes(self):
        """根据选择的音阶返回对应的音符"""
        scale_map = {
            "C大调": [0, 2, 4, 5, 7, 9, 11],  # C D E F G A B
            "A小调": [9, 11, 0, 2, 4, 5, 7],  # A B C D E F G
            "G大调": [7, 9, 11, 0, 2, 4, 6],  # G A B C D E F#
            "E小调": [4, 6, 7, 9, 11, 0, 2],  # E F# G A B C D
            "F大调": [5, 7, 9, 10, 0, 2, 4],  # F G A Bb C D E
            "D小调": [2, 4, 5, 7, 9, 10, 0],  # D E F G A Bb C
        }
        return scale_map.get(self.scale_var.get(), [0, 2, 4, 5, 7, 9, 11])
    
    def generate_rachmaninoff_style(self):
        """生成拉赫玛尼诺夫风格的旋律，包括打击乐器和弦乐伴奏"""
        self.track_notes = []
        ticks_per_beat = 480  # 标准MIDI分辨率
        current_time = 0
        
        # 获取当前选择的音阶
        scale = self.get_scale_notes()
        scale_root = scale[0]  # 音阶的根音
        
        # 计算音阶偏移量
        scale_offset = scale_root - 0  # 相对于C大调的偏移
        
        # 生成多个变奏
        num_variations = self.bars_var.get() // 2  # 每两小节一个变奏
        
        for variation in range(num_variations):
            # 主旋律（钢琴）
            for theme_note in self.rachmaninoff_theme:
                # 添加一些随机变化
                note_offset = random.randint(-2, 2)  # 随机音高变化
                duration_factor = random.uniform(0.8, 1.2)  # 随机节奏变化
                
                # 计算新的音符
                new_note = theme_note['note'] + scale_offset + note_offset
                new_duration = theme_note['duration'] * duration_factor
                
                # 确保音符在合理范围内
                new_note = max(48, min(84, new_note))  # 限制在C3到C6之间
                
                # 添加主旋律音符
                self.track_notes.append({
                    'note': new_note,
                    'velocity': random.randint(70, 100),  # 随机力度
                    'start': current_time,
                    'end': current_time + int(new_duration * ticks_per_beat),
                    'instrument': self.instruments["钢琴"]
                })
                
                # 添加弦乐伴奏（和弦）
                if random.random() < 0.7:  # 70%的概率添加和弦
                    chord_notes = [
                        new_note - 12,  # 低八度
                        new_note - 7,   # 纯五度
                        new_note - 4    # 大三度
                    ]
                    for chord_note in chord_notes:
                        if 36 <= chord_note <= 72:  # 确保和弦音符在合理范围内
                            self.track_notes.append({
                                'note': chord_note,
                                'velocity': random.randint(50, 70),  # 较弱的力度
                                'start': current_time,
                                'end': current_time + int(new_duration * ticks_per_beat),
                                'instrument': self.instruments["弦乐合奏"]
                            })
                
                # 添加打击乐器
                if current_time % (ticks_per_beat * 2) == 0:  # 每两拍添加一次
                    # 定音鼓
                    self.track_notes.append({
                        'note': 36,  # C2
                        'velocity': random.randint(60, 80),
                        'start': current_time,
                        'end': current_time + int(0.5 * ticks_per_beat),
                        'instrument': self.instruments["定音鼓"]
                    })
                    # 三角铁
                    self.track_notes.append({
                        'note': 76,  # E5
                        'velocity': random.randint(40, 60),
                        'start': current_time,
                        'end': current_time + int(0.1 * ticks_per_beat),
                        'instrument': self.instruments["三角铁"]
                    })
                
                current_time += int(new_duration * ticks_per_beat)
            
            # 添加一些装饰音
            if random.random() < 0.3:  # 30%的概率添加装饰音
                grace_note = {
                    'note': new_note + random.choice([-2, 2]),  # 上或下装饰音
                    'velocity': 80,
                    'start': current_time - int(0.1 * ticks_per_beat),
                    'end': current_time,
                    'instrument': self.instruments["钢琴"]
                }
                self.track_notes.append(grace_note)
    
    def generate_music(self):
        """生成MIDI音乐"""
        self.status_var.set("正在生成音乐...")
        self.root.update()
        
        # 清空之前的音符
        self.track_notes = []
        self.tempo = self.tempo_var.get()
        
        # 根据选择的模式生成音乐
        if self.mode_var.get() == "拉赫玛尼诺夫风格":
            self.generate_rachmaninoff_style()
        else:
            # 原有的随机生成逻辑
            num_bars = self.bars_var.get()
            beats_per_bar = self.time_signature[0]
            ticks_per_beat = 480  # 标准MIDI分辨率
            
            # 获取当前选择的音阶
            scale = self.get_scale_notes()
            
            # 生成旋律
            for bar in range(num_bars):
                # 每小节的节拍数
                for beat in range(beats_per_bar):
                    # 随机决定此拍是否有音符
                    if random.random() > 0.2:  # 80%几率有音符
                        # 随机选择音阶中的音符
                        scale_note = random.choice(scale)
                        # 在选定的八度范围内随机选择一个八度
                        octave = random.randint(self.octave_range[0], self.octave_range[1])
                        # 计算MIDI音符值 (C3 = 60)
                        note = 60 + scale_note + (octave - 3) * 12
                        
                        # 随机决定音符长度 (1/4, 1/8, 1/16拍等)
                        duration_options = [0.25, 0.5, 1.0]  # 以拍为单位
                        duration = random.choice(duration_options)
                        
                        # 随机决定音符力度 (音量)
                        velocity = random.randint(60, 100)
                        
                        # 计算音符开始时间 (以tick为单位)
                        start_time = (bar * beats_per_bar + beat) * ticks_per_beat
                        # 计算音符持续时间 (以tick为单位)
                        note_duration = int(duration * ticks_per_beat)
                        
                        # 存储音符信息
                        self.track_notes.append({
                            'note': note,
                            'velocity': velocity,
                            'start': start_time,
                            'end': start_time + note_duration
                        })
        
        # 绘制音符
        self.draw_notes()
        self.status_var.set(f"已生成 {len(self.track_notes)} 个音符")
    
    def draw_notes(self):
        """在画布上绘制音符"""
        self.canvas.delete("all")
        
        if not self.track_notes:
            return
        
        # 计算时间范围
        max_time = max(note['end'] for note in self.track_notes)
        min_note = min(note['note'] for note in self.track_notes)
        max_note = max(note['note'] for note in self.track_notes)
        note_range = max_note - min_note + 1
        
        # 设置画布大小和缩放
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # 留出边距
        margin_x = 50
        margin_y = 20
        
        # 绘制时间刻度
        ticks_per_beat = 480
        beats_per_bar = self.time_signature[0]
        bar_width = (canvas_width - 2 * margin_x) / (max_time / (ticks_per_beat * beats_per_bar)) 
        
        # 绘制小节线和标记
        for bar in range(int(max_time / (ticks_per_beat * beats_per_bar)) + 1):
            x = margin_x + bar * bar_width
            self.canvas.create_line(x, margin_y, x, canvas_height - margin_y, fill="#dddddd")
            self.canvas.create_text(x, canvas_height - margin_y + 10, text=f"{bar+1}", fill="#666666")
        
        # 绘制音高刻度（每个八度）
        for octave in range(self.octave_range[0], self.octave_range[1] + 1):
            y = margin_y + (max_note - (60 + (octave - 3) * 12)) * (canvas_height - 2 * margin_y) / note_range
            self.canvas.create_text(margin_x - 20, y, text=f"C{octave}", fill="#666666")
            
        # 绘制音符
        for note in self.track_notes:
            x1 = margin_x + note['start'] * (canvas_width - 2 * margin_x) / max_time
            x2 = margin_x + note['end'] * (canvas_width - 2 * margin_x) / max_time
            y = margin_y + (max_note - note['note']) * (canvas_height - 2 * margin_y) / note_range
            
            # 音符高度
            note_height = 10
            
            # 根据音符力度调整颜色
            intensity = int(155 * (note['velocity'] / 127)) + 100
            color = f"#{intensity:02x}{intensity//2:02x}ff"
            
            # 绘制音符矩形
            self.canvas.create_rectangle(x1, y - note_height/2, x2, y + note_height/2, 
                                        fill=color, outline="#000000")
            
            # 添加音符名称显示
            note_name = self.get_note_name(note['note'])
            self.canvas.create_text((x1 + x2) / 2, y, text=note_name, fill="#000000", font=("Arial", 8))
    
    def get_note_name(self, midi_note):
        """根据MIDI音符值返回音符名称"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = notes[midi_note % 12]
        return f"{note}{octave}"
    
    def create_midi_file(self):
        """从生成的音符创建MIDI文件"""
        midi_file = mido.MidiFile()
        track = mido.MidiTrack()
        midi_file.tracks.append(track)
        
        # 设置速度
        tempo_in_microseconds = mido.bpm2tempo(self.tempo)
        track.append(mido.MetaMessage('set_tempo', tempo=tempo_in_microseconds))
        
        # 设置拍号
        track.append(mido.MetaMessage('time_signature', numerator=self.time_signature[0],
                                     denominator=self.time_signature[1]))
        
        # 按开始时间排序音符
        sorted_notes = sorted(self.track_notes, key=lambda x: x['start'])
        
        # 添加音符
        current_time = 0
        current_instrument = None
        
        for note in sorted_notes:
            # 计算与上一个事件的时间差（以tick为单位）
            delta_time = note['start'] - current_time
            
            # 如果乐器改变，添加乐器变更消息
            if 'instrument' in note and note['instrument'] != current_instrument:
                track.append(mido.Message('program_change', program=note['instrument'], time=delta_time))
                current_instrument = note['instrument']
                delta_time = 0  # 重置时间差
            
            # 添加音符开始事件
            track.append(mido.Message('note_on', note=note['note'], 
                                     velocity=note['velocity'], time=delta_time))
            
            # 更新当前时间
            current_time = note['start']
            
            # 计算音符持续时间
            note_duration = note['end'] - note['start']
            
            # 添加音符结束事件
            track.append(mido.Message('note_off', note=note['note'], 
                                     velocity=0, time=note_duration))
            
            # 更新当前时间
            current_time = note['end']
        
        return midi_file
    
    def play_music(self):
        """实时播放生成的MIDI音乐"""
        if not self.track_notes or self.playing:
            return
            
        if self.midi_out is None:
            self.try_initialize_midi()
            if self.midi_out is None:
                messagebox.showerror("播放错误", "无法初始化MIDI输出。请检查MIDI设备连接。")
                return
        
        self.playing = True
        self.status_var.set("正在播放...")
        
        # 在新线程中播放MIDI，避免阻塞GUI
        def playback_thread():
            try:
                # 按开始时间排序音符
                sorted_notes = sorted(self.track_notes, key=lambda x: x['start'])
                
                # 当前活跃的音符，用于跟踪哪些音符需要关闭
                active_notes = {}
                
                # 计算播放开始时间
                start_time = time.time()
                
                # 转换tick为秒
                ticks_per_beat = 480
                seconds_per_tick = 60.0 / (self.tempo * ticks_per_beat)
                
                # 创建音符开始和结束事件的列表
                events = []
                
                for note in sorted_notes:
                    # 添加乐器变更事件
                    if 'instrument' in note:
                        events.append({
                            'time': note['start'],
                            'type': 'program_change',
                            'program': note['instrument']
                        })
                    
                    # 添加音符开始事件
                    events.append({
                        'time': note['start'],
                        'type': 'note_on',
                        'note': note['note'],
                        'velocity': note['velocity']
                    })
                    
                    # 添加音符结束事件
                    events.append({
                        'time': note['end'],
                        'type': 'note_off',
                        'note': note['note'],
                        'velocity': 0
                    })
                
                # 按时间排序所有事件
                events.sort(key=lambda x: x['time'])
                
                # 记录上一个事件的时间
                last_event_time = 0
                
                # 依次处理每个事件
                for event in events:
                    if not self.playing:
                        break
                    
                    # 计算需要等待的时间
                    wait_time = (event['time'] - last_event_time) * seconds_per_tick
                    
                    if wait_time > 0:
                        time.sleep(wait_time)
                    
                    # 更新播放指示器位置
                    self.update_position_indicator(event['time'])
                    
                    # 处理事件
                    if event['type'] == 'program_change':
                        # 发送MIDI乐器变更消息
                        self.midi_out.send_message([0xC0, event['program']])
                    elif event['type'] == 'note_on':
                        # 发送MIDI音符开始消息
                        self.midi_out.send_message([0x90, event['note'], event['velocity']])
                    else:  # note_off
                        # 发送MIDI音符结束消息
                        self.midi_out.send_message([0x80, event['note'], 0])
                    
                    # 更新上一个事件时间
                    last_event_time = event['time']
                
                # 关闭所有可能仍在播放的音符
                for note in range(128):
                    self.midi_out.send_message([0x80, note, 0])
                
                # 播放完成
                if self.playing:
                    self.playing = False
                    self.status_var.set("播放完成")
                    
                    # 清除播放指示器
                    if self.position_line:
                        self.canvas.delete(self.position_line)
                        self.position_line = None
                
            except Exception as e:
                messagebox.showerror("播放错误", f"播放时出错: {str(e)}")
                self.playing = False
                self.status_var.set("播放错误")
        
        # 启动播放线程
        threading.Thread(target=playback_thread, daemon=True).start()
    
    def update_position_indicator(self, current_tick):
        """更新画布上的播放位置指示器"""
        if not self.track_notes:
            return
            
        # 在主线程中更新UI
        def update_ui():
            # 删除旧的位置指示器
            if self.position_line:
                self.canvas.delete(self.position_line)
            
            # 计算位置
            max_time = max(note['end'] for note in self.track_notes)
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            margin_x = 50
            margin_y = 20
            
            x = margin_x + current_tick * (canvas_width - 2 * margin_x) / max_time
            
            # 绘制新的位置指示器
            self.position_line = self.canvas.create_line(
                x, margin_y, x, canvas_height - margin_y, 
                fill="#ff0000", width=2, dash=(4, 4)
            )
        
        # 在主线程中执行UI更新
        self.root.after(0, update_ui)
    
    def stop_music(self):
        """停止播放音乐"""
        if self.playing:
            self.playing = False
            self.status_var.set("播放已停止")
            
            # 关闭所有可能仍在播放的音符
            if self.midi_out:
                for note in range(128):
                    self.midi_out.send_message([0x80, note, 0])
            
            # 清除播放指示器
            if self.position_line:
                self.canvas.delete(self.position_line)
                self.position_line = None
    
    def save_midi(self):
        """保存MIDI文件"""
        if not self.track_notes:
            messagebox.showwarning("保存错误", "没有可保存的音符。请先生成音乐。")
            return
            
        # 创建MIDI文件
        midi_file = self.create_midi_file()
        
        # 打开文件选择对话框
        filename = filedialog.asksaveasfilename(
            defaultextension=".mid",
            filetypes=[("MIDI文件", "*.mid"), ("所有文件", "*.*")],
            title="保存MIDI文件"
        )
        
        if filename:
            try:
                midi_file.save(filename)
                self.status_var.set(f"MIDI文件已保存: {filename}")
            except Exception as e:
                messagebox.showerror("保存错误", f"无法保存MIDI文件: {str(e)}")
                self.status_var.set("保存失败")
    
    def on_closing(self):
        """窗口关闭时清理资源"""
        # 停止播放
        self.stop_music()
        
        # 关闭MIDI输出
        if self.midi_out:
            self.midi_out.close_port()
        
        # 销毁窗口
        self.root.destroy()

def main():
    # 创建主窗口
    root = tk.Tk()
    app = MidiComposer(root)
    
    # 窗口大小变化时重绘音符
    def on_resize(event):
        if hasattr(app, 'track_notes') and app.track_notes:
            app.draw_notes()
    
    app.canvas.bind('<Configure>', on_resize)
    
    root.mainloop()

if __name__ == "__main__":
    main() 