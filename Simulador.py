import tkinter as tk
from tkinter import messagebox
import sqlite3
from datetime import datetime

# -------------------------
# BASE DE DATOS
# -------------------------

def crear_db():
    conn = sqlite3.connect("prestamos.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prestamos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        capital REAL,
        interes REAL,
        meses INTEGER,
        cuota REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pagos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prestamo_id INTEGER,
        fecha TEXT,
        tipo TEXT,
        valor REAL,
        saldo REAL
    )
    """)

    conn.commit()
    conn.close()

crear_db()

prestamo_id = None
saldo_actual = 0
cuota_mensual = 0

# -------------------------
# CREAR PRESTAMO
# -------------------------

def crear_prestamo():

    global prestamo_id
    global saldo_actual
    global cuota_mensual

    try:
        meses = int(entry_meses.get())
    except:
        messagebox.showerror("Error","Ingrese meses válidos")
        return

    capital = 2250000
    interes = 1.8
    i = interes / 100

    cuota = capital * (i*(1+i)**meses)/((1+i)**meses-1)
    cuota = round(cuota,2)

    conn = sqlite3.connect("prestamos.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO prestamos(capital,interes,meses,cuota)
    VALUES(?,?,?,?)
    """,(capital,interes,meses,cuota))

    prestamo_id = cursor.lastrowid
    saldo_actual = capital
    cuota_mensual = cuota

    conn.commit()
    conn.close()

    label_cuota.config(text=f"Cuota mensual: ${cuota}")
    label_saldo.config(text=f"Saldo actual: ${saldo_actual}")

# -------------------------
# PAGAR CUOTA
# -------------------------

def pagar_cuota():

    global saldo_actual

    if prestamo_id is None:
        messagebox.showerror("Error","Primero cree un préstamo")
        return

    saldo_actual -= cuota_mensual

    if saldo_actual < 0:
        saldo_actual = 0

    conn = sqlite3.connect("prestamos.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO pagos(prestamo_id,fecha,tipo,valor,saldo)
    VALUES(?,?,?,?,?)
    """,(prestamo_id,datetime.now().strftime("%Y-%m-%d %H:%M"),"Cuota mensual",cuota_mensual,saldo_actual))

    conn.commit()
    conn.close()

    label_saldo.config(text=f"Saldo actual: ${saldo_actual}")

    messagebox.showinfo("Pago","Cuota pagada correctamente")

# -------------------------
# ABONO CAPITAL
# -------------------------

def abonar():

    global saldo_actual

    if prestamo_id is None:
        messagebox.showerror("Error","Primero cree un préstamo")
        return

    try:
        valor = float(entry_abono.get())
    except:
        messagebox.showerror("Error","Ingrese un valor válido")
        return

    saldo_actual -= valor

    if saldo_actual < 0:
        saldo_actual = 0

    conn = sqlite3.connect("prestamos.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO pagos(prestamo_id,fecha,tipo,valor,saldo)
    VALUES(?,?,?,?,?)
    """,(prestamo_id,datetime.now().strftime("%Y-%m-%d %H:%M"),"Abono capital",valor,saldo_actual))

    conn.commit()
    conn.close()

    label_saldo.config(text=f"Saldo actual: ${saldo_actual}")

    messagebox.showinfo("Abono",f"Nuevo saldo: {saldo_actual}")

# -------------------------
# HISTORIAL
# -------------------------

def ver_historial():

    if prestamo_id is None:
        messagebox.showerror("Error","Primero cree un préstamo")
        return

    conn = sqlite3.connect("prestamos.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT fecha,tipo,valor,saldo
    FROM pagos
    WHERE prestamo_id=?
    """,(prestamo_id,))

    pagos = cursor.fetchall()

    texto.delete(1.0,tk.END)

    for p in pagos:
        texto.insert(tk.END,f"{p[0]} | {p[1]} | ${p[2]} | Saldo: ${p[3]}\n")

    conn.close()

# -------------------------
# INTERFAZ BONITA
# -------------------------

ventana = tk.Tk()
ventana.title("Sistema de Préstamos")
ventana.geometry("520x520")
ventana.configure(bg="#f2f2f2")

titulo = tk.Label(
    ventana,
    text="Simulador de Préstamos",
    font=("Arial",18,"bold"),
    bg="#f2f2f2"
)
titulo.pack(pady=10)

frame = tk.Frame(ventana,bg="#f2f2f2")
frame.pack()

tk.Label(frame,text="Meses del préstamo:",bg="#f2f2f2").grid(row=0,column=0)

entry_meses = tk.Entry(frame,width=10)
entry_meses.grid(row=0,column=1,padx=5)

tk.Button(
    frame,
    text="Crear préstamo",
    bg="#4CAF50",
    fg="white",
    command=crear_prestamo
).grid(row=0,column=2,padx=10)

label_cuota = tk.Label(ventana,text="",bg="#f2f2f2",font=("Arial",11))
label_cuota.pack(pady=5)

label_saldo = tk.Label(
    ventana,
    text="Saldo actual: $0",
    font=("Arial",12,"bold"),
    bg="#f2f2f2"
)
label_saldo.pack(pady=5)

# BOTON PAGAR CUOTA

tk.Button(
    ventana,
    text="Pagar cuota mensual",
    bg="#2196F3",
    fg="white",
    width=25,
    command=pagar_cuota
).pack(pady=8)

# ABONO

tk.Label(ventana,text="Abono a capital",bg="#f2f2f2").pack()

entry_abono = tk.Entry(ventana,width=15)
entry_abono.pack()

tk.Button(
    ventana,
    text="Realizar abono",
    bg="#FF9800",
    fg="white",
    command=abonar
).pack(pady=6)

# HISTORIAL

tk.Button(
    ventana,
    text="Ver historial de pagos",
    command=ver_historial
).pack(pady=8)

texto = tk.Text(ventana,height=14,width=55)
texto.pack()

ventana.mainloop()