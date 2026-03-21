import sqlite3
from datetime import datetime, timedelta
from tabulate import tabulate
from colorama import Fore, Style, init

# Inicializar Colorama
init(autoreset=True)

# ===== Base de datos =====
conn = sqlite3.connect("prestamos.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS prestamos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    monto_inicial REAL,
    saldo REAL,
    meses INTEGER,
    tasa REAL,
    fecha_inicio TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS abonos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prestamo_id INTEGER,
    fecha TEXT,
    monto REAL,
    interes REAL,
    capital REAL,
    saldo_restante REAL,
    FOREIGN KEY (prestamo_id) REFERENCES prestamos(id)
)
""")
conn.commit()

# ===== Clase Prestamo =====
class PrestamoBanco:
    def __init__(self, prestamo_id=None, monto=None, meses=None, tasa_mensual=0.018):
        self.tasa_mensual = tasa_mensual
        if prestamo_id:
            self.id = prestamo_id
            cursor.execute("SELECT monto_inicial, saldo, meses, tasa, fecha_inicio FROM prestamos WHERE id=?", (prestamo_id,))
            self.monto_inicial, self.saldo, self.meses, self.tasa_mensual, fecha = cursor.fetchone()
            self.fecha_inicio = datetime.strptime(fecha, "%Y-%m-%d")
        else:
            self.monto_inicial = monto
            self.saldo = monto
            self.meses = meses
            self.fecha_inicio = datetime.today()
            cursor.execute("""
                INSERT INTO prestamos (monto_inicial, saldo, meses, tasa, fecha_inicio)
                VALUES (?, ?, ?, ?, ?)""",
                (self.monto_inicial, self.saldo, self.meses, self.tasa_mensual,
                 self.fecha_inicio.strftime("%Y-%m-%d"))
            )
            conn.commit()
            self.id = cursor.lastrowid

        self.cargar_abonos()
        self.generar_calendario()

    def cargar_abonos(self):
        cursor.execute("""
            SELECT fecha, monto, interes, capital, saldo_restante
            FROM abonos WHERE prestamo_id=?
            ORDER BY id""", (self.id,))
        self.abonos = [
            {'Fecha': f, 'Monto': m, 'Interés': i, 'Capital': c, 'Saldo': s}
            for f, m, i, c, s in cursor.fetchall()
        ]

    def generar_calendario(self):
        self.calendario = []
        saldo_temp = self.saldo
        meses_restantes = max(self.meses - len(self.abonos), 1)

        for i in range(1, meses_restantes + 1):
            interes = round(saldo_temp * self.tasa_mensual, 2)
            saldo_temp += interes
            capital_estimado = round(saldo_temp / (meses_restantes - i + 1), 2)
            saldo_temp -= capital_estimado

            self.calendario.append({
                'Mes': i,
                'Fecha': (datetime.today() + timedelta(days=30*i)).strftime('%Y-%m-%d'),
                'Interés': interes,
                'Capital': capital_estimado,
                'Saldo': saldo_temp
            })

    def abonar(self, monto):
        if monto <= 0:
            print(Fore.RED + "❌ El abono debe ser mayor a cero.")
            return

        interes = round(self.saldo * self.tasa_mensual, 2)
        self.saldo += interes
        abono_capital = monto
        self.saldo -= abono_capital
        saldo_restante = max(self.saldo, 0)

        fecha = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO abonos (prestamo_id, fecha, monto, interes, capital, saldo_restante)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (self.id, fecha, monto, interes, abono_capital, saldo_restante)
        )
        conn.commit()

        self.abonos.append({
            'Fecha': fecha,
            'Monto': monto,
            'Interés': interes,
            'Capital': abono_capital,
            'Saldo': saldo_restante
        })

        print(Fore.GREEN + f"✔ Abono de ${monto:.2f} registrado!")
        print(Fore.RED + f"💰 Saldo pendiente: ${saldo_restante:.2f}")
        self.generar_calendario()

    def mostrar_calendario(self):
        tabla = []
        for c in self.calendario:
            tabla.append([
                c['Mes'],
                c['Fecha'],
                Fore.YELLOW + f"${c['Interés']:.2f}" + Style.RESET_ALL,
                Fore.GREEN + f"${c['Capital']:.2f}" + Style.RESET_ALL,
                Fore.RED + f"${c['Saldo']:.2f}" + Style.RESET_ALL
            ])
        print("\n" + tabulate(tabla, headers=["Mes","Fecha","Interés","Capital","Saldo"], tablefmt="fancy_grid"))

    def mostrar_abonos(self):
        if not self.abonos:
            print(Fore.CYAN + "No hay abonos todavía.")
            return

        tabla = []
        for a in self.abonos:
            tabla.append([
                a['Fecha'],
                f"${a['Monto']:.2f}",
                Fore.YELLOW + f"${a['Interés']:.2f}" + Style.RESET_ALL,
                Fore.GREEN + f"${a['Capital']:.2f}" + Style.RESET_ALL,
                Fore.RED + f"${a['Saldo']:.2f}" + Style.RESET_ALL
            ])
        print("\n" + tabulate(tabla, headers=["Fecha","Monto","Interés","Capital","Saldo"], tablefmt="fancy_grid"))

    def progreso(self):
        pagado = self.monto_inicial - self.saldo
        porcentaje = min(max(pagado / self.monto_inicial * 100, 0), 100)

        barras = 30
        completas = int((porcentaje / 100) * barras)
        resto = barras - completas

        print(Fore.CYAN + "\n📊 Progreso del préstamo:")
        print(Fore.GREEN + "█" * completas + Fore.WHITE + "░" * resto,
              f"{porcentaje:.2f}% pagado")

# ===== Menús =====
def menu_principal():
    while True:
        print(Fore.CYAN + "\n=== SISTEMA DE PRÉSTAMOS (Estilo Bancario) ===")
        print("1. Crear nuevo préstamo")
        print("2. Cargar préstamo existente")
        print("3. Salir")
        opc = input("Seleccione aquí: ")

        if opc == "1":
            monto = float(input("Monto del préstamo: "))
            meses = int(input("Plazo en meses: "))
            prestamo = PrestamoBanco(monto=monto, meses=meses)
            menu_prestamo(prestamo)

        elif opc == "2":
            cursor.execute("SELECT id, monto_inicial, saldo FROM prestamos")
            prestamos = cursor.fetchall()
            if not prestamos:
                print(Fore.RED + "⚠ No hay préstamos guardados.")
                continue

            print("\n📋 Préstamos existentes:")
            for p in prestamos:
                print(f"ID {p[0]} — Inicial: ${p[1]:.2f}, Saldo: ${p[2]:.2f}")
            pid = int(input("Ingrese el ID a cargar: "))
            prestamo = PrestamoBanco(prestamo_id=pid)
            menu_prestamo(prestamo)

        elif opc == "3":
            print(Fore.CYAN + "👋 ¡Hasta pronto!")
            break

        else:
            print(Fore.RED + "❌ Opción inválida.")

def menu_prestamo(prestamo):
    while True:
        print(Fore.CYAN + "\n--- MENÚ DE OPERACIONES ---")
        print("1. Ver calendario de pagos")
        print("2. Hacer un abono")
        print("3. Ver historial de pagos")
        print("4. Ver progreso del préstamo")
        print("5. Volver")
        opt = input("Seleccione: ")

        if opt == "1":
            prestamo.mostrar_calendario()
        elif opt == "2":
            pago = float(input("Monto a abonar: "))
            prestamo.abonar(pago)
        elif opt == "3":
            prestamo.mostrar_abonos()
        elif opt == "4":
            prestamo.progreso()
        elif opt == "5":
            break
        else:
            print(Fore.RED + "❌ Opción inválida.")

menu_principal()