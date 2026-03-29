import sqlite3
from datetime import datetime, timedelta
from tabulate import tabulate
from colorama import Fore, Style, init
import os
import time


# ===== UTILIDADES =====

def pausa():
    input(
        Fore.YELLOW +
        "\n╔═══════════════════════════╗\n"
        "║ Press. ENTER For continue ║\n"
        "╚═══════════════════════════╝"
    )


def limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")


def pantalla_inicio():

    limpiar_pantalla()

    print(Fore.CYAN + """
╔══════════════════════╗
║ SISTEMA DE PRÉSTAMOS ║
╚══════════════════════╝
""")

    pasos = [
        (Fore.YELLOW, "Iniciando sistema..."),
        (Fore.GREEN, "✔ Cargando módulos..."),
        (Fore.GREEN, "✔ Conectando base de datos..."),
        (Fore.GREEN, "✔ Preparando interfaz...")
    ]

    for color, mensaje in pasos:
        print(color + mensaje)
        time.sleep(0.6)

    print(Fore.MAGENTA + "\nSistema listo 🚀")
    time.sleep(1.2)

    limpiar_pantalla()


# ===== CALCULADORA =====

class CalculadoraPrestamo:

    @staticmethod
    def interes_total(monto, tasa, meses):
        return round(monto * tasa * meses, 2)

    @staticmethod
    def monto_total(monto, tasa, meses):
        return round(monto + CalculadoraPrestamo.interes_total(monto, tasa, meses), 2)

    @staticmethod
    def interes_cuota(saldo, tasa):
        return round(saldo * tasa, 2)

    @staticmethod
    def dividir_pago(cuota, interes):
        return round(cuota - interes, 2)


# ===== COLORAMA =====
init(autoreset=True)


# ===== BASE DE DATOS =====

conn = sqlite3.connect("prestamos.db")
cursor = conn.cursor()

# Crear columna tipo si no existe
try:
    cursor.execute("ALTER TABLE abonos ADD COLUMN tipo TEXT")
    conn.commit()
except:
    pass
cursor.execute("UPDATE abonos SET tipo='ABONO' WHERE tipo IS NULL")
conn.commit()

# Activar claves foráneas (mejor integridad)
cursor.execute("PRAGMA foreign_keys = ON")


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
CREATE TABLE IF NOT EXISTS cuotas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prestamo_id INTEGER,
    mes INTEGER,
    fecha TEXT,
    cuota REAL,
    interes REAL,
    capital REAL,
    saldo REAL,
    estado TEXT DEFAULT 'pendiente'
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
    saldo_restante REAL
)
""")

conn.commit()


# ===== CLASE PRINCIPAL =====

class PrestamoColor:

    def __init__(self, prestamo_id=None, monto=None, meses=None, tasa_mensual=0.018):

        self.tasa_mensual = tasa_mensual

        # ===== CARGAR PRÉSTAMO EXISTENTE =====
        if prestamo_id:

            self.id = prestamo_id

            cursor.execute(
                "SELECT monto_inicial, saldo, meses, tasa, fecha_inicio FROM prestamos WHERE id=?",
                (prestamo_id,)
            )

            datos = cursor.fetchone()

            if not datos:
                raise ValueError("El préstamo no existe")

            self.monto_inicial, self.saldo, self.meses, self.tasa_mensual, fecha = datos

            self.monto = self.monto_inicial
            self.interes_pagado = 0

            self.fecha_inicio = datetime.strptime(fecha, "%Y-%m-%d")

        # ===== CREAR NUEVO PRÉSTAMO =====
        else:

            self.monto_inicial = monto
            self.saldo = monto
            self.meses = meses
            self.monto = monto
            self.fecha_inicio = datetime.today()

            cursor.execute("""
            INSERT INTO prestamos (monto_inicial, saldo, meses, tasa, fecha_inicio)
            VALUES (?,?,?,?,?)
            """, (
                self.monto_inicial,
                self.saldo,
                self.meses,
                self.tasa_mensual,
                self.fecha_inicio.strftime("%Y-%m-%d")
            ))

            conn.commit()
            self.id = cursor.lastrowid

        self.cargar_cuotas()
        self.cargar_abonos()

        if not self.cuotas:
            self.generar_cuotas()

    def eliminar_abono(self, abono_id):

        cursor.execute(
            "SELECT monto FROM abonos WHERE id = ? AND prestamo_id = ?",
            (abono_id, self.id)
        )
        abono = cursor.fetchone()

        if not abono:
            print(Fore.RED + "╔════════════════════════╗")
            print(Fore.RED + "║ ❌ Abono no encontrado ║")
            print(Fore.RED + "╚════════════════════════╝")
            return

        monto = abono[0]

        # Restaurar saldo
        self.saldo = round(self.saldo + monto, 2)

        # Eliminar abono
        cursor.execute("DELETE FROM abonos WHERE id = ?", (abono_id,))

        # Actualizar saldo en BD
        self.actualizar_saldo_db()

        conn.commit()

        # 🔹 Recargar abonos
        self.cargar_abonos()

        # 🔹 RECALCULAR CUOTAS
        self.recalcular_cuotas()

        print(Fore.GREEN + "╔══════════════════════════════════╗")
        print(Fore.GREEN + f"║ ✔ Abono eliminado: ${monto:.2f}".ljust(34) + "║")
        print(Fore.YELLOW + f"║ 💰 Saldo restaurado: ${self.saldo:.2f}".ljust(31) + "║")
        print(Fore.GREEN + "╚══════════════════════════════════╝")

    # ===== RECALCULAR CUOTAS =====

    def recalcular_cuotas(self):

        if self.saldo <= 0:
            cursor.execute("DELETE FROM cuotas WHERE prestamo_id=?", (self.id,))
            conn.commit()
            self.cuotas = []
            return

        # eliminar solo cuotas pendientes
        cursor.execute("""
        DELETE FROM cuotas
        WHERE prestamo_id=? AND estado='pendiente'
        """, (self.id,))

        conn.commit()

        # generar nuevas cuotas con el saldo actual
        self.generar_cuotas()

    # ===== ACTUALIZAR SALDO =====

    def actualizar_saldo_db(self):

        cursor.execute(
            "UPDATE prestamos SET saldo=? WHERE id=?",
            (self.saldo, self.id)
        )

        conn.commit()

    # ===== CARGAR CUOTAS =====

    def cargar_cuotas(self):

        cursor.execute(
            """
            SELECT id,mes,fecha,cuota,interes,capital,saldo,estado
            FROM cuotas
            WHERE prestamo_id=?
            ORDER BY mes
            """,
            (self.id,)
        )

        self.cuotas = [
            {
                'id': cid,
                'Mes': m,
                'Fecha': f,
                'Cuota': c,
                'Interés': i,
                'Capital': cap,
                'Saldo': s,
                'Estado': e
            }
            for cid, m, f, c, i, cap, s, e in cursor.fetchall()
        ]

    # ===== CARGAR ABONOS =====

    def cargar_abonos(self):

        cursor.execute("""
        SELECT id, fecha, monto, interes, capital, saldo_restante, tipo
        FROM abonos
        WHERE prestamo_id = ?
        ORDER BY fecha
        """, (self.id,))

        datos = cursor.fetchall()

        self.abonos = []

        for d in datos:
            self.abonos.append({
                "id": d[0],
                "Fecha": d[1],
                "Monto": d[2],
                "Interés": d[3],
                "Capital": d[4],
                "Saldo": d[5],
                "tipo": d[6]
            })

    # ===== CUOTA MENSUAL =====

    def cuota_mensual(self):

        P = self.monto_inicial
        r = self.tasa_mensual
        n = self.meses

        cuota = P * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

        return round(cuota, 2)

    # ===== RESUMEN FINANCIERO =====

    def interes_total_prestamo(self):

        cuota = self.cuota_mensual()
        total_pagado = cuota * self.meses
        interes_total = total_pagado - self.monto_inicial

        return round(interes_total, 2)

    def total_a_pagar(self):

        cuota = self.cuota_mensual()

        return round(cuota * self.meses, 2)

    def interes_restante(self):

        total_interes = self.interes_total_prestamo()

        capital_pagado = self.monto_inicial - self.saldo

        if self.monto_inicial == 0:
            return 0

        interes_restante = total_interes - (
            total_interes * (capital_pagado / self.monto_inicial)
        )

        return round(max(interes_restante, 0), 2)


    def resumen_financiero(self):

            pagado = self.monto_inicial - self.saldo

            progreso = 0
            if self.monto_inicial > 0:
                progreso = pagado / self.monto_inicial

            cuota = self.cuota_mensual()
            total = self.total_a_pagar()
            interes_total = self.interes_total_prestamo()
            interes_restante = self.interes_restante()

            interes = interes_total - interes_restante

            largo = 35
            llenado = int(largo * progreso)

            barra = "█" * llenado + "░" * (largo - llenado)
            porcentaje = progreso * 100

            print(Fore.GREEN  + f"║ Monto del préstamo : ${self.monto_inicial:>10.2f} ║")
            print(Fore.YELLOW + f"║ Tasa mensual       : {self.tasa_mensual*100:>10.2f}% ║")
            print(Fore.BLUE   + f"║ Cuota mensual      : ${cuota:>10.2f} ║")

            print(Fore.CYAN + "╠══════════════════════════════════╣")
            print(Fore.MAGENTA + "║             TOTALES              ║")
            print(Fore.CYAN + "╠══════════════════════════════════╣")

            print(Fore.GREEN  + f"║ Total a pagar      : ${total:>10.2f} ║")
            print(Fore.YELLOW + f"║ Interés total      : ${interes_total:>10.2f} ║")

            print(Fore.CYAN + "╠══════════════════════════════════╣")
            print(Fore.MAGENTA + "║         TOTALES PAGADOS          ║")
            print(Fore.CYAN + "╠══════════════════════════════════╣")

            print(Fore.GREEN + f"║ Saldo pagado       : ${pagado:>10.2f} ║")
            print(Fore.YELLOW + f"║ Interés Pagado     : ${interes:>10.2f} ║")

            print(Fore.CYAN + "╠══════════════════════════════════╣")
            print(Fore.RED + "║          ESTADO ACTUAL           ║")
            print(Fore.CYAN + "╠══════════════════════════════════╣")

            print(Fore.CYAN   + f"║ Saldo restante     : ${self.saldo:>10.2f} ║")
            print(Fore.YELLOW + f"║ Interés restante   : ${interes_restante:>10.2f} ║")

            print(Fore.CYAN + "╚══════════════════════════════════╝")

            if porcentaje > 100:
                porcentaje = 100

            print("\n" + Fore.MAGENTA + f"[{barra}] {porcentaje:.2f}%")

            if porcentaje >= 99.99:
                print(Fore.GREEN + "\n🎉 ¡Préstamo completamente pagado! 🎉")


    def generar_cuotas(self):

        saldo_temp = round(self.saldo, 2)
        cuota = self.cuota_mensual()

        cursor.execute(
            "DELETE FROM cuotas WHERE prestamo_id=?",
            (self.id,)
        )

        for i in range(1, self.meses + 1):

            if saldo_temp <= 0:
                break

            interes = CalculadoraPrestamo.interes_cuota(
                saldo_temp,
                self.tasa_mensual
            )

            capital = CalculadoraPrestamo.dividir_pago(
                cuota,
                interes
            )

            if capital > saldo_temp:
                capital = saldo_temp
                cuota = round(capital + interes, 2)

            saldo_temp = round(saldo_temp - capital, 2)

            cursor.execute("""
            INSERT INTO cuotas
            (prestamo_id,mes,fecha,cuota,interes,capital,saldo,estado)
            VALUES (?,?,?,?,?,?,?,?)
            """,(
                self.id,
                i,
                (self.fecha_inicio + timedelta(days=30*i)).strftime('%Y-%m-%d'),
                cuota,
                interes,
                capital,
                max(saldo_temp,0),
                'pendiente'
            ))

        conn.commit()
        self.cargar_cuotas()


    def mostrar_cuotas(self):

        tabla = []

        for c in self.cuotas:

            estado = c['Estado']

            color_estado = Fore.GREEN if estado == 'pagada' else Fore.RED
            color_cuota = Fore.BLUE if estado == 'pendiente' else Fore.GREEN

            tabla.append([
                c['Mes'],
                c['Fecha'],
                color_cuota + f"${c['Cuota']:.2f}" + Style.RESET_ALL,
                Fore.RED + f"${c['Interés']:.2f}" + Style.RESET_ALL,
                Fore.CYAN + f"${c['Capital']:.2f}" + Style.RESET_ALL,
                Fore.RED + f"${c['Saldo']:.2f}" + Style.RESET_ALL,
                color_estado + estado + Style.RESET_ALL
            ])

        print("\n" + tabulate(
            tabla,
            headers=["Mes","Fecha","Cuota","Interés","Capital","Saldo","Estado"],
            tablefmt="fancy_grid"
        ))


    def pagar_cuota(self, mes):

        if self.saldo <= 0:
            print(Fore.RED + "⚠ El préstamo ya está completamente pagado.")
            return

        for c in self.cuotas:

            if c['Mes'] == mes:

                if c['Estado'] == 'pagada':
                    print(Fore.CYAN + "╔══════════════════════╗")
                    print(Fore.RED + f"║ ❌ Cuota {mes} ya pagada ║")
                    print(Fore.CYAN + "╚══════════════════════╝")
                    return

                monto = c['Cuota']
                interes = c['Interés']
                capital = c['Capital']

                self.saldo = round(self.saldo - capital, 2)

                fecha = datetime.today().strftime("%Y-%m-%d")

                cursor.execute("""
                INSERT INTO abonos (prestamo_id,fecha,monto,interes,capital,saldo_restante,tipo)
                VALUES (?,?,?,?,?,?,?)
                """, (
                    self.id,
                    fecha,
                    monto,
                    interes,
                    capital,
                    self.saldo,
                    "CUOTA"
                ))

                cursor.execute(
                    "UPDATE cuotas SET estado='pagada' WHERE id=?",
                    (c['id'],)
                )

                self.actualizar_saldo_db()
                conn.commit()

                self.cargar_cuotas()
                self.cargar_abonos()

                print(Fore.MAGENTA + "╔════════════════════════════════╗")
                print(Fore.GREEN + f"║ ✔ Cuota {mes} pagada correctamente ║")
                print(Fore.MAGENTA + "╚════════════════════════════════╝")

                return

        print(Fore.MAGENTA + "╔══════════════════════╗")
        print(Fore.RED + "║ ❌ Mes no encontrado ║")
        print(Fore.MAGENTA + "╚══════════════════════╝")


    def cambiar_estado_cuota(self, mes):

        for c in self.cuotas:

            if c['Mes'] == mes:

                if c['Estado'] == "pagada":

                    cursor.execute("""
                    SELECT id,capital FROM abonos
                    WHERE prestamo_id=? AND ABS(capital-?)<0.01
                    ORDER BY id DESC LIMIT 1
                    """,(self.id,c['Capital']))

                    pago = cursor.fetchone()

                    if pago:

                        pago_id, capital = pago

                        cursor.execute(
                            "DELETE FROM abonos WHERE id=?",
                            (pago_id,)
                        )

                        self.saldo = round(self.saldo + capital, 2)

                        self.actualizar_saldo_db()

                    cursor.execute(
                        "UPDATE cuotas SET estado='pendiente' WHERE id=?",
                        (c['id'],)
                    )

                    conn.commit()

                    self.cargar_cuotas()
                    self.cargar_abonos()

                    print(Fore.CYAN + "╔════════════════════════════════╗")
                    print(Fore.YELLOW + f"║ ✔ Cuota {mes} cambiada a pendiente ║")
                    print(Fore.CYAN + "╚════════════════════════════════╝")

                else:

                    print(Fore.CYAN + "╔══════════════════════════════════════════╗")
                    print(Fore.RED + "║ Use 'Pagar cuota' para registrar el pago ║")
                    print(Fore.CYAN + "╚══════════════════════════════════════════╝")

                return

        print(Fore.MAGENTA + "╔══════════════════════╗")
        print(Fore.RED + "║ ❌ Mes no encontrado ║")
        print(Fore.MAGENTA + "╚══════════════════════╝")

    def abonar_extra(self, monto):

            if monto <= 0:
                print(Fore.RED + "Monto inválido")
                return

            if self.saldo <= 0:
                print(Fore.RED + "⚠ El préstamo ya está completamente pagado.")
                return

            if monto > self.saldo:
                print(Fore.YELLOW + f"⚠ Solo se recibirá ${self.saldo:.2f}")
                monto = self.saldo

            saldo_anterior = self.saldo
            capital = monto
            interes_pagado = 0   # ⭐ los abonos no pagan interés

            # actualizar saldo
            self.saldo = round(self.saldo - capital, 2)

            if self.saldo < 0:
                self.saldo = 0

            fecha = datetime.today().strftime("%Y-%m-%d")

            cursor.execute("""
            INSERT INTO abonos (prestamo_id,fecha,monto,interes,capital,saldo_restante,tipo)
            VALUES (?,?,?,?,?,?,?)
            """, (
                self.id,
                fecha,
                monto,
                interes_pagado,
                capital,
                self.saldo,
                "ABONO"
            ))

            self.actualizar_saldo_db()
            conn.commit()

            self.cargar_abonos()

            # ⭐ recalcular cuotas con el nuevo saldo
            self.recalcular_cuotas()

            print(Fore.MAGENTA + "╔═══════════════════════════════════╗")
            print(Fore.CYAN + f"║ 💰 Saldo actual:    ║ ${saldo_anterior:.2f}".ljust(35) + "║")
            print(Fore.GREEN + f"║ ✔ Abono realizado:  ║ ${monto:.2f}".ljust(36) + "║")
            print(Fore.RED + f"║ 💰 Saldo restante:  ║ ${self.saldo:.2f}".ljust(35) + "║")
            print(Fore.MAGENTA + "╚═══════════════════════════════════╝")

            if self.saldo == 0:
                print(Fore.GREEN + "\n🎉 ¡Préstamo completamente pagado!")

    def eliminar_prestamo(self):

        print(Fore.CYAN + "+==============================================================+")
        confirm = input(Fore.RED + " |¿Seguro que desea eliminar este préstamo? (S/N): S=SI / N=NO | ")
        print(Fore.CYAN + "+==============================================================+")

        if confirm.upper() != "S":
            print(Fore.CYAN + "+==========================+")
            print(Fore.RED + "| Cancelado por el usuario |")
            print(Fore.CYAN + "+==========================+")
            return

        cursor.execute("DELETE FROM cuotas WHERE prestamo_id=?", (self.id,))
        cursor.execute("DELETE FROM abonos WHERE prestamo_id=?", (self.id,))
        cursor.execute("DELETE FROM prestamos WHERE id=?", (self.id,))

        conn.commit()

        print(Fore.CYAN + "+================================+")
        print(Fore.GREEN + "|Préstamo eliminado correctamente|")
        print(Fore.CYAN + "+================================+")
#erores 641
    def mostrar_abonos(self):

        if not self.abonos:
            return False

        tabla = []

        for a in self.abonos:

            if a["tipo"] == "CUOTA":
                tipo = Fore.BLUE + "CUOTA" + Style.RESET_ALL
                interes = a["Interés"]
                capital = a["Capital"]

            else:
                tipo = Fore.GREEN + "ABONO" + Style.RESET_ALL
                interes = 0
                capital = a["Monto"]

            tabla.append([
                a["id"],
                tipo,
                a["Fecha"],
                Fore.BLUE + f"${a['Monto']:.2f}" + Style.RESET_ALL,
                Fore.YELLOW + f"${interes:.2f}" + Style.RESET_ALL,
                Fore.CYAN + f"${capital:.2f}" + Style.RESET_ALL,
                Fore.RED + f"${a['Saldo']:.2f}" + Style.RESET_ALL
            ])

        print("\n" + tabulate(
            tabla,
            headers=["ID", "Tipo", "Fecha", "Monto", "Interés", "Capital", "Saldo"],
            tablefmt="fancy_grid"
        ))

        return True

def menu_principal():

    while True:

        limpiar_pantalla()

        print(Fore.RED + "╔══════════════════════╗")
        print(Fore.RED + "║ SISTEMA DE PRÉSTAMOS ║")
        print(Fore.RED + "╚══════════════════════╝")

        print(Fore.CYAN + "╔═══╗══════════════════╗")
        print(Fore.GREEN + "║ 1 ║  Crear préstamo  ║")
        print(Fore.CYAN + "╚═══╝══════════════════╝")

        print(Fore.CYAN + "╔═══╗══════════════════╗")
        print(Fore.GREEN + "║ 2 ║ Cargar préstamos ║")
        print(Fore.CYAN + "╚═══╝══════════════════╝")

        print(Fore.CYAN + "╔═══╗══════════════════╗")
        print(Fore.GREEN + "║ 3 ║ Salir            ║")
        print(Fore.CYAN + "╚═══╝══════════════════╝")

        print(Fore.CYAN + "╔══════════════════════╗")
        op = input(Fore.YELLOW + "║ Seleccione una opción: ")
        print(Fore.CYAN + "╚══════════════════════╝")

        # =========================
        # CREAR PRÉSTAMO
        # =========================
        if op == "1":

            limpiar_pantalla()

            # INGRESAR MONTO
            while True:
                try:
                    print(Fore.CYAN + "╔══════════════════════════╗")
                    print(Fore.CYAN + "║      NUEVO PRÉSTAMO      ║")
                    print(Fore.CYAN + "╠══════════════════════════╣")

                    monto = float(input(Fore.YELLOW + "║ Ingrese monto solicitado: "))

                    if monto <= 0:
                        print(Fore.RED + "╠══════════════════════════╣")
                        print(Fore.RED + "║ ❌ El monto debe ser mayor a 0 ║")
                        print(Fore.RED + "╠══════════════════════════╣")
                        continue

                    print(Fore.CYAN + "╠══════════════════════════╣")
                    break

                except ValueError:
                    print(Fore.RED + "╠══════════════════════════╣")
                    print(Fore.RED + "║ ❌ Ingrese número válido ║")
                    print(Fore.RED + "╠══════════════════════════╣")

            # INGRESAR MESES
            while True:
                try:
                    print(Fore.CYAN + "╔══════════════════════════╗")

                    meses = int(input(Fore.YELLOW + "║ Ingrese meses a pagar: "))

                    if meses <= 0:
                        print(Fore.RED + "╠══════════════════════════╣")
                        print(Fore.RED + "║ ❌ Meses deben ser mayor a 0 ║")
                        print(Fore.RED + "╠══════════════════════════╣")
                        continue

                    print(Fore.CYAN + "╠══════════════════════════╣")
                    break

                except ValueError:
                    print(Fore.RED + "╠══════════════════════════╣")
                    print(Fore.RED + "║ ❌ Ingrese número entero ║")
                    print(Fore.RED + "╠══════════════════════════╣")

            limpiar_pantalla()

            prestamo = PrestamoColor(monto=monto, meses=meses)

            menu_prestamo(prestamo)

        # =========================
        # CARGAR PRÉSTAMOS
        # =========================
        elif op == "2":

            limpiar_pantalla()

            cursor.execute("SELECT id, monto_inicial, saldo FROM prestamos")
            prestamos = cursor.fetchall()

            if not prestamos:

                print(Fore.RED + "╔═════════════════════════════════╗")
                print(Fore.RED + "║ ❌ No hay préstamos registrados ║")
                print(Fore.RED + "╚═════════════════════════════════╝")

                input(Fore.YELLOW + "| Presione Enter para continuar... ")
                continue

            print(Fore.RED + "╔═══════════════════════════════════╗")
            print(Fore.MAGENTA + "║       PRÉSTAMOS EXISTENTES        ║")
            print(Fore.RED + "╚═══════════════════════════════════╝")

            print(Fore.YELLOW + "+====+===============+==============+")
            print(Fore.GREEN + "| ID | MONTO INICIAL | SALDO ACTUAL |")
            print(Fore.YELLOW + "+====+===============+==============+")

            for p in prestamos:

                print(
                    Fore.CYAN +
                    f"| {p[0]:<3}| ${p[1]:<12.2f} | ${p[2]:<12.2f}|"
                )

            while True:
                try:
                    print(Fore.CYAN + "+====+===============+==============+")
                    pid = int(input(Fore.YELLOW + "| Ingrese ID del préstamo: "))
                    break

                except ValueError:

                    print(Fore.RED + "╔═══════════════════════════════════╗")
                    print(Fore.RED + "║ ❌ Debe ingresar un número válido ║")
                    print(Fore.RED + "╚═══════════════════════════════════╝")

            cursor.execute("SELECT id FROM prestamos WHERE id=?", (pid,))
            existe = cursor.fetchone()

            if not existe:

                print(Fore.RED + "╔═══════════════════════════╗")
                print(Fore.RED + "║ ❌ Ese préstamo no existe ║")
                print(Fore.RED + "╚═══════════════════════════╝")

                input(Fore.YELLOW + "| Presione Enter para continuar... ")
                continue

            prestamo = PrestamoColor(prestamo_id=pid)

            menu_prestamo(prestamo)

        # =========================
        # SALIR
        # =========================
        elif op == "3":

            print(Fore.MAGENTA + "╔══════════════════════╗")
            print(Fore.GREEN + "║ Gracias, hasta luego ║")
            print(Fore.MAGENTA + "╚══════════════════════╝")

            break

        # =========================
        # OPCIÓN INVÁLIDA
        # =========================
        else:

            print(Fore.RED + "╔══════════════════════╗")
            print(Fore.RED + "║  ❌ Opción inválida  ║")
            print(Fore.RED + "╚══════════════════════╝")

            input(Fore.YELLOW + "| Presione Enter para continuar... ")
    

def menu_prestamo(prestamo):

    while True:

        limpiar_pantalla()

        print(Fore.CYAN + "\n╔═══════════════════════════╗")
        print(Fore.CYAN + "║        MENÚ PRÉSTAMO      ║")
        print(Fore.CYAN + "╠════╦══════════════════════╣")
        print(Fore.GREEN + "║ 1  ║ Ver cuotas           ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 2  ║ Pagar cuota          ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 3  ║ Abono extra Capital  ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 4  ║ Historial pagos      ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 5  ║ Cambiar estado cuota ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 6  ║ Eliminar abono       ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 7  ║ Resumen financiero   ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 8  ║ Eliminar préstamo    ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 9  ║ Volver               ║")
        print(Fore.CYAN + "╚════╩══════════════════════╝")

        op = input(Fore.YELLOW + "║ Seleccione una opción: ")

        # ===================================
        # VER CUOTAS
        # ===================================
        if op == "1":

            limpiar_pantalla()

            print(Fore.CYAN + "╔════════════╗")
            print(Fore.CYAN + "║ VER CUOTAS ║")
            print(Fore.CYAN + "╚════════════╝")

            prestamo.mostrar_cuotas()

            pausa()

        # ===================================
        # PAGAR CUOTA
        # ===================================
        elif op == "2":

            limpiar_pantalla()

            print(Fore.CYAN + "╔═════════════╗")
            print(Fore.CYAN + "║ PAGAR CUOTA ║")
            print(Fore.CYAN + "╚═════════════╝")

            prestamo.mostrar_cuotas()

            try:

                print(Fore.RED + "╔═════════════════════════╗")
                mes = int(input(Fore.GREEN + "║ Número de cuota a pagar: "))
                print(Fore.RED + "╚═════════════════════════╝")

                prestamo.pagar_cuota(mes)

            except ValueError:

                print(Fore.RED + "╔═════════════════════╗")
                print(Fore.RED + "║ ❌ Entrada inválida ║")
                print(Fore.RED + "╚═════════════════════╝")

            pausa()

        # ===================================
        # ABONO EXTRA
        # ===================================
        elif op == "3":

            limpiar_pantalla()

            print(Fore.RED + "╔═════════════════════╗")
            print(Fore.CYAN + "║ ABONO EXTRA CAPITAL ║")
            print(Fore.RED + "╚═════════════════════╝")

            try:

                print(Fore.GREEN + "+=======================+")
                monto = float(input(Fore.YELLOW + "║ Monto a abonar: "))
                print(Fore.GREEN + "+=======================+")

                prestamo.abonar_extra(monto)

            except ValueError:

                print(Fore.RED + "╔════════════════════╗")
                print(Fore.RED + "║ ❌ Entrada inválida ║")
                print(Fore.RED + "╚════════════════════╝")

            pausa()

        # ===================================
        # HISTORIAL PAGOS
        # ===================================
        elif op == "4":

            limpiar_pantalla()

            print(Fore.CYAN + "╔════════════════════╗")
            print(Fore.CYAN + "║ HISTORIAL DE PAGOS ║")
            print(Fore.CYAN + "╚════════════════════╝")

            hay_abonos = prestamo.mostrar_abonos()

            if not hay_abonos:

                print(Fore.RED + "╔════════════════════════════╗")
                print(Fore.RED + "║  No hay pagos registrados  ║")
                print(Fore.RED + "╚════════════════════════════╝")

            pausa()

        # ===================================
        # CAMBIAR ESTADO CUOTA
        # ===================================
        elif op == "5":

            limpiar_pantalla()

            print(Fore.CYAN + "╔══════════════════════╗")
            print(Fore.CYAN + "║ CAMBIAR ESTADO CUOTA ║")
            print(Fore.CYAN + "╚══════════════════════╝")

            prestamo.mostrar_cuotas()

            try:

                mes = int(input(Fore.YELLOW + "| Número de cuota a modificar: "))

                prestamo.cambiar_estado_cuota(mes)

                print()
                print(Fore.CYAN + "╔═══════════════════════╗")
                print(Fore.CYAN + "║  CUOTAS ACTUALIZADAS  ║")
                print(Fore.CYAN + "╚═══════════════════════╝")

                prestamo.mostrar_cuotas()

            except ValueError:

                print(Fore.RED + "╔═══════════════════════╗")
                print(Fore.RED + "║  ❌ Entrada inválida  ║")
                print(Fore.RED + "╚═══════════════════════╝")

            pausa()

        # ===================================
        # ELIMINAR ABONO
        # ===================================
        elif op == "6":

            limpiar_pantalla()

            print(Fore.CYAN + "╔════════════════╗")
            print(Fore.CYAN + "║ ELIMINAR ABONO ║")
            print(Fore.CYAN + "╚════════════════╝")

            hay_abonos = prestamo.mostrar_abonos()

            if not hay_abonos:

                print(Fore.RED + "╔════════════════════════════╗")
                print(Fore.RED + "║  No hay abonos registrados ║")
                print(Fore.RED + "╚════════════════════════════╝")

            else:

                try:

                    abono_id = int(input(Fore.YELLOW + "| ID del abono: "))
                    prestamo.eliminar_abono(abono_id)

                except ValueError:

                    print(Fore.RED + "╔═════════════════════╗")
                    print(Fore.RED + "║ ❌ Entrada inválida ║")
                    print(Fore.RED + "╚═════════════════════╝")

            pausa()

        # ===================================
        # RESUMEN FINANCIERO
        # ===================================
        elif op == "7":

            limpiar_pantalla()

            print(Fore.CYAN + "╔══════════════════════════════════╗")
            print(Fore.CYAN + "║        RESUMEN FINANCIERO        ║")
            print(Fore.CYAN + "╚══════════════════════════════════╝")

            prestamo.resumen_financiero()

            pausa()

         # ELIMINAR PRESTAMO
        elif op == "8":

            limpiar_pantalla()

            print(Fore.RED + "+------------------------------------+")
            print(Fore.RED + "|         ELIMINAR PRÉSTAMO          |")
            print(Fore.RED + "+------------------------------------+")
            print(Fore.YELLOW + "|    ¿Seguro que desea eliminarlo?   |")
            print(Fore.YELLOW + "|  Esta acción no se puede deshacer  |")
            print(Fore.RED + "+------------------------------------+")

            print(Fore.CYAN + "+------------------+--------------+")
            confirm = input(Fore.CYAN + "| Confirmar (S/N): | S=SI / N=NO  |")
            print(Fore.CYAN + "+------------------+--------------+")

            if confirm.upper() == "S":

                prestamo.eliminar_prestamo()


                pausa()
                break

            else:

                print(Fore.YELLOW + "+---------------------------------+")
                print(Fore.YELLOW + "|       OPERACIÓN CANCELADA       |")
                print(Fore.YELLOW + "+---------------------------------+")

                pausa()

        # ===================================
        # VOLVER
        # ===================================
        elif op == "9":

            limpiar_pantalla()

            print(Fore.CYAN + "╔═══════════════════════════╗")
            print(Fore.CYAN + "║VOLVIENDO AL MENÚ PRINCIPAL║")
            print(Fore.CYAN + "╚═══════════════════════════╝")

            pausa()
            break

        # ===================================
        # OPCIÓN INVÁLIDA
        # ===================================
        else:

            print(Fore.RED + "╔═══════════════════════════╗")
            print(Fore.RED + "║     ❌ OPCIÓN INVÁLIDA    ║")
            print(Fore.RED + "╚═══════════════════════════╝")

            pausa()


pantalla_inicio()
menu_principal()