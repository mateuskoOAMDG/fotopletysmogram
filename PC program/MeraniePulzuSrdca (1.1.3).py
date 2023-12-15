# Meranie tepu srdca
# Aplikácia číta zo sérioveho portu dvojicu (dt,y)
# a zobrazuje v realnom čase + v nameranom vklada casove znacky lavym klikom mysi
# Jun 01, 2023 
# autor: mateusko O.A.M.D.G


import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror, showwarning, showinfo
import tkinter.font as fnt
import time
import serial
import os


debug_print = False

class ArduinoSerial:
    serial = serial.Serial()

    @staticmethod
    def get_ports():
        ports = []
        readports = os.popen("python -m serial.tools.list_ports").read().split('\n')
        for value in readports:
            value2 = value.strip()
            if len(value2) > 0:
                ports.append(value2)
        return ports

    def open(self, port, baudrate=115200, timeout=0.5):
        self.serial.port = port
        self.serial.baudrate = baudrate
        self.serial.timeout = timeout
        self.serial.open()


    def readline(self):
        """Prečíta riadok zo Serial, lebo vráti False, ak nie sú dátak dispozícii"""
        if (self.serial.in_waiting > 0):
            ans = self.serial.readline()
            ans = ans.decode("ascii", "replace")
            return ans
        return False

    def clear_buffer(self):
        """Vyprázdni vstupný buffer"""
        self.serial.reset_input_buffer()
        while self.serial.in_waiting > 0:
            self.serial.readall()

    def is_connected(self):
        return self.serial.isOpen()

    def close(self):
        self.serial.close()


class Graph:
    """Trieda obsluhujúca vykreslovanie grafu na Canvas"""

    def __init__(self, canvas, scrollbar, controller):
        self.controller = controller
        self._scrollbar = scrollbar  # odkaz na scrollbar, vyuziva sa jeho metoda get
        self._canvas = canvas  # tu sa graf vykresluje
        self._xcmin = 0  # xmin Canvasu
        self._xcmax = 0  # xmax Canvasu
        self._ycmin = 0  # ymin Canvasu
        self._ycmax = 0  # ymax Canvasu
        self._pad_y = -10 # top+bottom pad - okraj
        self._dx = 10  # x-ova vzdialenost medzi bodmi
        self._raw_y_data = []  # jednorozmerne pole dat "y"
        self._raw_y1_data = []  # jednorozmerne pole dat "y1" druhy graf - tu casova derivacia y
        self._min_y = 999999 # fotopletyzmograf
        self._max_y = 0
        self._min_y1 = 999999 # casova derivacia fotopletyzmografu
        self._max_y1 = -999999
        self._time_marks = [] #časové značky držia hodnotu "x" (coordinate x)
        self._graph_function = None
        self._graph_function1 = None
        self._x_axis = None
        self._sample_time = 40
        self._last_y = 0  # posledne zapísaná hodnota y do Listu
        self._derivative_var = None
        self._sum_y_data = 0

    def setDerivativeVar(self, var):
        self._derivative_var = var

    def clear(self):
        '''
        Vymazanie Canvasu
        '''
        self._canvas.delete("all")

    def range(self, xcmin, xcmax, ycmin, ycmax):
        '''definovanie range - vykreslovanej oblasti; rozmer celeho Canvasu'''
        self._xcmin = xcmin
        self._xcmax = xcmax
        self._ycmin = ycmin
        self._ycmax = ycmax

        self._canvas.config(scrollregion=(f'{xcmin} {ycmin} {xcmax} {ycmax}'))

    def range_x(self, xcmin, xcmax):
        """Nastavuje x-ovy rozmer celeho Canvasu"""
        self._xcmin = xcmin
        self._xcmax = xcmax
        self._canvas.config(scrollregion=(f'{self._xcmin} {self._ycmin} {self._xcmax} {self._ycmax}'))

    def autorange_x(self):
        self._xcmax = max(len(self._raw_y_data) * self._dx, 800)
        self._canvas.config(scrollregion=(f'{self._xcmin} {self._ycmin} {self._xcmax} {self._ycmax}'))

    def scaley(self, ymin, ymax):
        '''definovanie scale - mierky osi y grafu'''
        self._ymin = ymin
        self._ymax = ymax
        ok = ymin != ymax
        if ok:
            self._koef_y = float(self._ycmax - self._ycmin - 2 * self._pad_y) / (ymax - ymin)
        return ok

    def scaley1(self, ymin1, ymax1):
        '''definovanie scale - mierky osi y grafu'''
        self._ymin1 = ymin1
        self._ymax1 = ymax1
        ok = ymin1 != ymax1
        if ok:
            self._koef_y1 = float(self._ycmax - self._ycmin - 2 * self._pad_y) / (ymax1 - ymin1)
        return ok


    def get_visible_range_x(self):
        """Vráti tuple (xmin, xmax) viditeľej časti canvasu"""
        scr_xmin, scr_xmax = self._scrollbar.get()
        max_x = int((self._canvas.cget('scrollregion').split(" "))[2])
        xmin = int(scr_xmin * max_x)
        xmax = int(scr_xmax * max_x)
        if debug_print:
            print(f'Visible: [{scr_xmin}, {scr_xmax}]; [{xmin}, {xmax}]')
        return ((xmin, xmax))

    def auto_scale_y_from_visible(self):
        xmin, xmax = self.get_visible_range_x()
        xmin = int(xmin / self._dx)
        xmax = int(xmax / self._dx)
        ymin = min(self._raw_y_data[xmin:xmax])
        ymax = max(self._raw_y_data[xmin:xmax])
        return self.scaley(ymin, ymax)

    def auto_scale_y1_from_visible(self):
        if self._derivative_var.get() == 1:
            xmin, xmax = self.get_visible_range_x()
            xmin = int(xmin / self._dx)
            xmax = int(xmax / self._dx)
            ymin1 = min(self._raw_y1_data[xmin:xmax])
            ymax1 = max(self._raw_y1_data[xmin:xmax])
            yamp = max(abs(ymin1), abs(ymax1))
            return self.scaley1(-yamp, yamp)
        return None

    def auto_scale_y_from_all(self):
        ymin = min(self._raw_y_data)
        ymax = max(self._raw_y_data)

        return self.scaley(ymin, ymax)

    def auto_scale_y1_from_all(self):
        ymin1 = min(self._raw_y1_data)
        ymax1 = max(self._raw_y1_data)
        yamp = max(abs(ymin1), abs(ymax1))
        return self.scaley1(-yamp, yamp)

    def add_y(self, y):

        self._raw_y_data.append(y)

        y1 = y - self._last_y
        self._last_y = y
        if y1 > 0:
            y1 = 0
            self._raw_y1_data.append(self._sum_y_data)
            self._sum_y_data = 0
        else:
            self._sum_y_data += abs(y1)
            self._raw_y1_data.append(0)


        self._min_y = min(y, self._min_y)
        self._max_y = max(y, self._max_y)

        self._min_y1 = min(y1, self._min_y1)
        self._max_y1 = max(y1, self._max_y1)

    def delete_last(self, n):
        try:
            for i in range(n):
                self._raw_y_data.pop()
        except :
            pass
        finally:
            pass

    def delete_last1(self, n):
        try:
            for i in range(n):
                self._raw_y1_data.pop()
        except:
            pass
        finally:
            pass

    def delete_data(self):
        self._raw_y_data = []
        self._graph_function = None
        self._time_marks = []
        self.clear()

    def delete_data1(self):
        self._raw_y1_data = []
        self._graph_function1 = None
        self._canvas.delete("hist")
        self.clear()

    def yr(self, y):
        """ Vypocet strojovej súradnice"""
        return (y - self._ymin) * self._koef_y + self._ycmin + self._pad_y

    def yr1(self, y):
        """ Vypocet strojovej súradnice"""
        return (y - self._ymin1) * self._koef_y1 + self._ycmin + self._pad_y

    def transform(self):
        '''vytvorenie dvorozmerneho pola bodov na vykreslenie z
           self._raw_y_data = []'''
        data = []
        x = -self._dx
        for value in self._raw_y_data:
            x += self._dx
            y = (value - self._ymin) * self._koef_y + self._ycmin + self._pad_y
            data.append((x, y))
        return data

    def transform1(self):

        '''vytvorenie dvojrozmerneho pola bodov na vykreslenie z
           self._raw_y_data = []'''
        if self._derivative_var.get() == 1:
            data = []
            x = -self._dx
            for value in self._raw_y1_data:
                x += self._dx
                y = (value - self._ymin1) * self._koef_y1 + self._ycmin + self._pad_y
                data.append((x, y))
            return data

    def min_y_raw(self):
        return min(self._raw_y_data)

    def min_y1_raw(self):
        return min(self._raw_y1_data)

    def max_y_raw(self):
        return max(self._raw_y_data)

    def max_y1_raw(self):
        return max(self._raw_y1_data)

    def draw(self):
        if len(self._raw_y_data) >= 2:
            if self._graph_function:
                self._canvas.delete(self._graph_function)
            self._graph_function = self._canvas.create_line(self.transform(), fill="blue", width=2)
        self.drawXAxis()

    def draw1(self):
        self._canvas.delete("hist")
        if self._derivative_var.get() == 1:
            if len(self._raw_y1_data) >= 2:

                #self._graph_function1 = self._canvas.create_line(self.transform1(), fill="green")
                for (x, y) in self.transform1():
                    self._canvas.create_rectangle(x-10, self.yr1(0), x-3, y, fill="lightgreen", tags="hist",
                                                  outline="lightgreen")
            self.drawXAxis1()

    def drawXAxis(self):
        if self._x_axis:
            self._canvas.delete("axis_x")
        # kreslenie osi
        self._x_axis = self._canvas.create_line(0, self._ycmin - 10, self._xcmax, self._ycmin - 10, fill="darkgreen", tags="axis_x")
        # kreslenie ciarok
        x = 0
        sec = 1
        while ( x < self._xcmax):
            x = int(sec / self._sample_time * self._dx * 1000)
            self._canvas.create_line(x, self._ycmin - 15, x, self._ycmin - 5, fill="darkgreen", tags="axis_x")
            self._canvas.create_text(x, self._ycmin - 25, text=str(sec) + " s", tags="axis_x",fill="darkgreen")
            sec += 1

    def drawXAxis1(self):
        if self._x_axis:
            self._canvas.delete("axis_x1")
        # kreslenie osi
        y = self.yr1(0)
        self._x_axis = self._canvas.create_line(0, y, self._xcmax, y, fill="yellow", tags="axis_x1")

    def get_raw_data(self):
        return self._raw_y_data

    def min_y_index(self, index1, count):
        index2 = index1 + count
        return min(self._raw_y_data[index1:index2])

    def max_y_index(self, index1, count):
        index2 = index1 + count
        return max(self._raw_y_data[index1:index2])

    def get_mark_index(self, event):
        dx, dy = self._scrollbar.get()
        sr = int((self._canvas.cget('scrollregion').split(" "))[2])

        x = int(event.x + dx * sr) - 2

        i = round(x / self._dx)
        return i

    def add_time_mark(self, event):
        i = self.get_mark_index(event)
        if debug_print:
            print(f'Index: {i}')
        mark = self.get_mark_by_index(i)
        if debug_print:
            print(f'mark = {mark}')
        if mark:
            return

        time = i / 1000 * self._sample_time

        mark_text = self._canvas.create_text(i * 10 + 2, 20, text=f't={time:.2f} s', anchor=tk.SW, fill="red")
        mark_line = self._canvas.create_line(i * 10, 0, i * 10, 300, fill="red")
        mark_index = i

        self._time_marks.append((mark_index, mark_line, mark_text))
        self.controller.view.status_text("Počet označených intervalov " + self.get_count_timemarks())


    def get_mark_by_index(self, index):
        for mark in self._time_marks:
            mark_index, mark_line, mark_text = mark
            if index == mark_index:
                return mark
        return False

    def delete_mark_by_index(self, index):
        i = 0
        while i < len(self._time_marks):
            mark_index = self._time_marks[i][0]
            if index == mark_index:
                self._canvas.delete(self._time_marks[i][1])
                self._canvas.delete(self._time_marks[i][2])
                self._time_marks[i] = ((-1, None, None))
                self.controller.view.status_text("Počet označených intervalov " + self.get_count_timemarks())
                break
            i += 1

    def get_count_timemarks(self):
        cnt = 0
        for item in self._time_marks:
            if item[0] != -1:
                cnt += 1
        if cnt == 0:
            return "(žiadna značka)"
        else:
            return str(cnt - 1)

    def clear_time_mark(self, event):
        i = self.get_mark_index(event)
        if debug_print:
            print(f'Clear time mark i={i}')
        self.delete_mark_by_index(i)

    def set_sample_time(self, value):
        self._sample_time = float(value)

class VstupnyPortView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        _application = parent
        self.controller = None
        options = {'padx': 5, 'pady': 5}

        # frame POrt Select

        self.port_frame = ttk.Frame(self)

        # label Select Port
        self.label = ttk.Label(self.port_frame, text='Vstupný port:')
        self.label.grid(column=0, row=0)

        # combo box Ports
        self.selected_port = tk.StringVar()
        self.combobox = ttk.Combobox(self.port_frame, textvariable=self.selected_port)
        self.combobox['values'] = ArduinoSerial.get_ports()
        self.combobox['state'] = 'readonly'
        self.combobox.grid(column=1, row=0)

        # button Connect
        self.connect_button_state = False  # disconnected
        self.button = ttk.Button(self.port_frame, text='Pripojiť')

        self.button['command'] = self.button_connect_clicked
        self.button.grid(column=2, row=0)

        # show the frame on the container

        # label connected
        self.label_connected = ttk.Label(self.port_frame, text='')
        self.label_connected.grid(column=3, row=0)
        self.show_disconnected()

        self.port_frame.grid(row=0, column=0, sticky="w")

        # end of frame Port Select

        # frame SampleTime
        # --- Sample Time
        self.sample_time_frame = ttk.Frame(self)
        self.sample_time_variable = tk.StringVar()
        self.sample_time_variable.set('40')

        self.sample_time_label = ttk.Label(self.sample_time_frame, text="Vzorkovací čas (ms):")
        self.sample_time_combobox = ttk.Combobox(self.sample_time_frame, values=['20','25','40','50','100'],
                                                state='readonly', textvariable=self.sample_time_variable, width=4)
        self.sample_time_combobox.bind('<<ComboboxSelected>>', self.set_sample_time)

        self.sample_time_label.grid(row=0, column=0)
        self.sample_time_combobox.grid(row=0, column=1)
        self.sample_time_frame.grid(row=0, column=1, sticky="w")

        # --- Treshold

        self.treshold_variable = tk.StringVar()
        self.treshold_variable.set('')
        self.treshold_label = ttk.Label(self.sample_time_frame, text="Spúšťacia úroveň:")
        self.treshold_entry = ttk.Entry(self.sample_time_frame, textvariable=self.treshold_variable)
        self.treshold_entry.bind('<Return>', self.treshold_return_pressed)
        self.treshold_label.grid(row=0, column=2, sticky="w")
        self.treshold_entry.grid(row=0, column=3, sticky="w")

        # frame Canvas
        self.canvas_frame = ttk.Frame(self)
        self.scrollbar = ttk.Scrollbar(self.canvas_frame, orient='horizontal')
        self.canvas = tk.Canvas(self.canvas_frame, height=300, width=800, bg="white", scrollregion=(0, 0, 800, 400),
                                xscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Button-1>", self.print_item)
        self.canvas.bind("<Button-3>", self.delete_item)
        self.scrollbar.config(command=self.scrolldata)

        self.canvas.grid(row=0, column=0, sticky="we")
        self.scrollbar.grid(row=1, column=0, sticky="we")

        self.canvas_frame.grid(row=1, column=0, columnspan=2, sticky="we")
        # end of frame Canvas

        # frame Buttons
        self.buttons_frame = ttk.Frame(self)

        self.start_button = ttk.Button(self.buttons_frame, text='Štart', command=self.button_start_clicked, width="8")
        self.start_button.grid(row=1, column=1, sticky="ns")

        self.stop_button = ttk.Button(self.buttons_frame, text='Stop', command=self.button_stop_clicked, width="8")
        self.stop_button.grid(row=2, column=1, sticky="ns")

        self.zoom1_button = ttk.Button(self.buttons_frame, text='Mierka\nviditeľné', command=self.zoom1_button_clicked, width="8")
        self.zoom1_button.grid(row=3, column=1, sticky="ns")

        self.zoom2_button = ttk.Button(self.buttons_frame, text='Mierka\ncelé', command=self.zoom2_button_clicked, width="8")
        self.zoom2_button.grid(row=4, column=1, sticky="ns")

        self.autoscale_variable = tk.IntVar(master=self, value=1)
        self.autoscale_check = ttk.Checkbutton(self.buttons_frame, text="Mierka\nauto", variable= self.autoscale_variable ,onvalue = 1, offvalue = 0)
        self.autoscale_check.grid(row=5, column=1, sticky="ns")

        self.derivative_variable = tk.IntVar(master=self, value=1)
        self.autoscale_check = ttk.Checkbutton(self.buttons_frame, text="Derivácia",
                                               variable=self.derivative_variable, onvalue=1, offvalue=0)
        self.autoscale_check.grid(row=6, column=1, sticky="ns")

        self.exit_button = ttk.Button(self.buttons_frame, text='Koniec', command=self.button_exit_clicked, width="8")
        self.exit_button.grid(row=7, column=1, sticky="ns")

        self.buttons_frame.grid(row=0, column=2, rowspan=2, sticky="we")
        # end of frame buttons

        self.status_label = ttk.Label(self, text="Vitaj!!!", font=("Times", 16))
        self.status_label.grid(row=2, column=0, columnspan=3, sticky="we")

        self.capturing_off()
        self.status_text("Vitajte v Laboratóriu fyziky GSA! Najprv pripojte Arduino na vstupný port.")

        self.start_active(False)

        self.controller = None

    def scrolldata(self, *x):
        if debug_print:
            print(f'scrolldata x={x}')
        self.canvas.xview(*x)
        if not self.controller.start_status and (self.autoscale_variable.get() == 1):
            self.controller.zoom_visible()


    

    def print_item(self, event):
        self.controller.print_item(event)

    def delete_item(self, event):
        self.controller.delete_item(event)



    def button_connect_clicked(self):
        if self.controller:
            if self.connect_button_state:
                self.controller.disconnect()
            else:
                value = self.selected_port.get()
                if value:
                    self.controller.connect(value)
        self.combobox['values'] = ArduinoSerial.get_ports()

    def button_start_clicked(self):
        self.controller.capture_start()

    def button_stop_clicked(self):
        self.controller.capture_stop()

    def zoom1_button_clicked(self):
        self.controller.zoom_visible()

    def zoom2_button_clicked(self):
        self.controller.zoom_all()

    def button_exit_clicked(self):
        self.controller.exit()

    def show_connected(self):
        self.label_connected['text'] = 'Pripojené'
        self.label_connected['foreground'] = 'green'
        self.button['text'] = 'Odpojiť'
        self.combobox.config(state="disabled")
        self.connect_button_state = True

    def show_disconnected(self):
        self.label_connected['text'] = 'Nepripojené'
        self.label_connected['foreground'] = 'red'
        self.button['text'] = 'Pripojiť'
        self.connect_button_state = False
        self.combobox.config(state="enabled")

    def status_text(self, the_text):
        self.status_label.config(text=the_text)

    def set_controller(self, controller):
        self.controller = controller

    def update_ports(self):
        self.combobox['values'] = ArduinoSerial.get_ports()

    def capturing_active(self):
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.zoom1_button.config(state=tk.DISABLED)
        self.zoom2_button.config(state=tk.DISABLED)

    def capturing_off(self):
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.zoom1_button.config(state=tk.NORMAL)
        self.zoom2_button.config(state=tk.NORMAL)

    def start_active(self, active):
        if active:
            self.start_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.DISABLED)

    def update_canvas(self):
        self.canvas.update()
        self.status_label.update()

    def set_sample_time(self, event):
        self.controller.set_sample_time(self.sample_time_variable.get())

    def treshold_return_pressed(self, event):
        self.treshold_entry.focus()
        self.controller.set_treshold(self.treshold_variable.get())

class Model:
    serial = None
    sample_time = 40

    def __init__(self):
        self.serial = ArduinoSerial()

    def open_port(self, port):
        self.serial.open(port)


class Controller:
    def __init__(self, model, view, application):
        self.model = model
        self.view = view
        self.graph = Graph(view.canvas, view.scrollbar, self)
        self.application = application
        self.start_status = False
        self.treshold = 8000
        self.view.treshold_variable.set(str(self.treshold))
        self.graph.setDerivativeVar(self.view.derivative_variable)

    def connect(self, port):
        self.view.update_ports()
        try:
            self.model.serial.open(port)
            self.view.show_connected()
            self.view.start_active(True)
        except:
            self.view.show_disconnected()
            showerror("Chyba pripojenia", f"K portu {port} sa nedá pripojiť.")

    def disconnect(self):
        self.model.serial.close()
        self.view.show_disconnected()

    def capture_start(self):
        self.view.capturing_active()
        self.start_status = True
        self.capturing()

    def capture_stop(self):
        self.view.capturing_off()
        self.start_status = False
        self.zoom_visible()

    def zoom_visible(self):
        self.graph.auto_scale_y_from_visible()
        self.graph.auto_scale_y1_from_visible()

        self.graph.draw1()
        self.graph.draw()

    def zoom_all(self):
        self.graph.auto_scale_y_from_all()
        self.graph.auto_scale_y1_from_all()

        self.graph.draw1()
        self.graph.draw()

    def print_item(self, event):
        self.graph.add_time_mark(event)

    def delete_item(self, event):
        self.graph.clear_time_mark(event)

    def set_sample_time(self, value):
        self.graph._sample_time = float(value)
        if debug_print:
            print(f'Sample time set to {value} ms')

    def set_treshold(self, value):
        try:
            value = int(value)
            if value < 0 or value > 200000:
                raise ValueError("")
            self.treshold = value
            showinfo("Info", f"Spúšťacia úroveň bola nastavená na {value}")
        except:
            showwarning("Chyba","Neplatná hodnota")
            self.view.treshold_variable.set("0")
            self.treshold = 0

    def exit(self):
        self.capture_stop()
        self.disconnect()
        quit()

    # vykonna procedura obstaravajuca citanie dat zo serial
    # a ich nasledne kreslenie na canvas
    def capturing(self):
        if not self.model.serial.is_connected():
            self.view.status_text("Najprv otvorte port.")
            showerror("Chyba pripojenia", "Port nie je otvorený")
            return

        self.view.capturing_active()


        self.view.status_text("Položte prst na senzor a vydržte, kým sa nezobrazí graf.")

        self.graph.range(0, 800, 300, 0)

        self.graph.clear()
        self.graph.delete_data()  #graf
        self.graph.delete_data1()   #derivacia
        self.view.update_canvas()

        old_value = -1
        stop = 10
        self.model.serial.clear_buffer()
        running = True
        stoptext = "Načítanie dát zo senzora skončilo."
        timer = time.perf_counter()
        treshold_run = False
        try:
            while running and self.start_status:
                if (time.perf_counter() - timer > 3) and (stop != 0):
                    stoptext = "Senzor nereaguje, skontrolujte pripojenie!"
                    running = False
                    continue

                self.application.update()
                ans = self.model.serial.readline()

                if not ans:
                    continue
                if debug_print:
                    print(ans)
                try:
                    ans = int(ans.strip().split(',')[1])
                    print(ans)
                except:
                    continue

                timer = time.perf_counter()

                if debug_print:
                    print(f'Add y = {ans}')

                if not treshold_run:
                    if ans > self.treshold:
                        treshold_run = True
                    else:
                        continue
                else:
                    if ans < self.treshold:
                        self.graph.delete_last(3)
                        self.graph.delete_last1(3)
                        running = False
                        continue

                self.graph.add_y(ans)

                self.graph.autorange_x()
                if self.graph.auto_scale_y_from_visible():
                    self.graph.clear()

                    if self.graph.auto_scale_y1_from_visible():
                        self.graph.draw1()
                    self.graph.draw()
                    self.view.canvas.xview("moveto", "1")
                    self.view.canvas.update()
                    self.view.scrollbar.update()



            self.view.status_text(stoptext)
            self.capture_stop()

        except serial.SerialException:
            self.capture_stop()
            self.disconnect()
            showerror("Chyba", "Vyskytla sa chyba pri komunikácii s Arduinom.")
            self.view.status_text("")

        except Exception as err:
            showerror("Chyba", f"Vyskytla sa chyba pri komunikácii s Arduinom: {err}, {type(err)}")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.major_version = "1"
        self.minor_version = "1"
        self.patch_version = "3"
        version = ".".join((self.major_version,self.minor_version,self.patch_version))
        self.title(f'Meranie frekvencie tepu srdca s Arduinom {version}  (GSA 2023)')

        model = Model()

        view = VstupnyPortView(self)
        view.pack()
        controller = Controller(model, view, self)

        view.set_controller(controller)


if __name__ == "__main__":
    app = App()

    app.mainloop()
