import sqlite3
from datetime import datetime, timedelta
from tabulate import tabulate
from colorama import Fore, Style, init
import os
import time
import msvcrt

def pausa():
    print(Fore.YELLOW + "\n| Presione cualquier tecla para continuar... ")
    msvcrt.getch()

def limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")


def pantalla_inicio():

    limpiar_pantalla()

    print(Fore.CYAN + """
================================
      SISTEMA DE PRÉSTAMOS
================================
""")

    print(Fore.YELLOW + "Iniciando sistema...")
    time.sleep(0.6)

    print(Fore.GREEN + "✔ Cargando módulos...")
    time.sleep(0.6)

    print(Fore.GREEN + "✔ Conectando base de datos...")
    time.sleep(0.6)

    print(Fore.GREEN + "✔ Preparando interfaz...")
    time.sleep(0.6)

    print(Fore.MAGENTA + "\nSistema listo 🚀")
    time.sleep(1.2)

    limpiar_pantalla()

class CalculadoraPrestamo:

    @staticmethod
    def interes_total(monto, tasa, meses):
        return monto * tasa * meses

    @staticmethod
    def monto_total(monto, tasa, meses):
        interes = CalculadoraPrestamo.interes_total(monto, tasa, meses)
        return monto + interes

    @staticmethod
    def interes_cuota(saldo, tasa):
        return round(saldo * tasa, 2)

    @staticmethod
    def dividir_pago(cuota, interes):
        capital = round(cuota - interes, 2)
        return capital

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


class PrestamoColor:

    def __init__(self, prestamo_id=None, monto=None, meses=None, tasa_mensual=0.018):

        self.tasa_mensual = tasa_mensual

        if prestamo_id:

            self.id = prestamo_id

            cursor.execute(
                "SELECT monto_inicial, saldo, meses, tasa, fecha_inicio FROM prestamos WHERE id=?",
                (prestamo_id,)
            )

            self.monto_inicial, self.saldo, self.meses, self.tasa_mensual, fecha = cursor.fetchone()

            self.monto = self.monto_inicial   # ⭐ ESTA LÍNEA ARREGLA TU ERROR

            self.fecha_inicio = datetime.strptime(fecha, "%Y-%m-%d")

        else:

            self.monto_inicial = CalculadoraPrestamo.monto_total(monto, self.tasa_mensual, meses)
            self.saldo = self.monto_inicial
            self.meses = meses
            self.monto = self.monto_inicial   # ⭐ IMPORTANTE
            self.fecha_inicio = datetime.today()

            cursor.execute("""
            INSERT INTO prestamos (monto_inicial, saldo, meses, tasa, fecha_inicio
            VALUES (?,?,?,?,?)
            """,(self.monto_inicial,self.saldo,self.meses,self.tasa_mensual,self.fecha_inicio.strftime("%Y-%m-%d")))

            conn.commit()
            self.id = cursor.lastrowid

        self.cargar_cuotas()
        self.cargar_abonos()

        if not self.cuotas:
            self.generar_cuotas()

    def actualizar_saldo_db(self):

        cursor.execute(
            "UPDATE prestamos SET saldo=? WHERE id=?",
            (self.saldo,self.id)
        )

        conn.commit()

    def cargar_cuotas(self):

        cursor.execute(
            "SELECT id,mes,fecha,cuota,interes,capital,saldo,estado FROM cuotas WHERE prestamo_id=? ORDER BY mes",
            (self.id,)
        )

        self.cuotas=[
            {'id':cid,'Mes':m,'Fecha':f,'Cuota':c,'Interés':i,'Capital':cap,'Saldo':s,'Estado':e}
            for cid,m,f,c,i,cap,s,e in cursor.fetchall()
        ]

    def cargar_abonos(self):

        cursor.execute(
            "SELECT id,fecha,monto,interes,capital,saldo_restante FROM abonos WHERE prestamo_id=? ORDER BY id",
            (self.id,)
        )

        self.abonos=[
            {'id':i,'Fecha':f,'Monto':m,'Interés':inte,'Capital':c,'Saldo':s}
            for i,f,m,inte,c,s in cursor.fetchall()
        ]

    def cuota_mensual(self):

        P=self.monto_inicial
        r=self.tasa_mensual
        n=self.meses

        cuota=P*(r*(1+r)**n)/((1+r)**n-1)
        return round(cuota,2)

        # ===== RESUMEN FINANCIERO DEL PRÉSTAMO =====

    def interes_total_prestamo(self):

        cuota = self.cuota_mensual()
        total_pagado = cuota * self.meses
        interes_total = total_pagado - self.monto_inicial

        return round(interes_total,2)


    def total_a_pagar(self):

        cuota = self.cuota_mensual()
        total = cuota * self.meses

        return round(total,2)


    def interes_restante(self):

        total_interes = self.interes_total_prestamo()

        capital_pagado = self.monto_inicial - self.saldo

        interes_restante = total_interes - capital_pagado

        if interes_restante < 0:
            interes_restante = 0

        return round(interes_restante,2)


    def resumen_financiero(self):

        cuota = self.cuota_mensual()
        total = self.total_a_pagar()
        interes_total = self.interes_total_prestamo()
        interes_restante = self.interes_restante()

        print(Fore.CYAN+"\n=========== RESUMEN FINANCIERO ===========")

        print(Fore.GREEN+f"Monto del préstamo : ${self.monto_inicial:.2f}")
        print(Fore.YELLOW+f"Tasa mensual       : {self.tasa_mensual*100:.2f}%")
        print(Fore.BLUE+f"Cuota mensual      : ${cuota:.2f}")

        print(Fore.MAGENTA+"\n------ Totales ------")

        print(Fore.GREEN+f"Total a pagar      : ${total:.2f}")
        print(Fore.YELLOW+f"Interés total      : ${interes_total:.2f}")

        print(Fore.RED+"\n------ Estado actual ------")

        print(Fore.CYAN+f"Saldo restante     : ${self.saldo:.2f}")
        print(Fore.YELLOW+f"Interés restante   : ${interes_restante:.2f}")

    def generar_cuotas(self):

        saldo_temp=self.monto_inicial
        cuota=self.cuota_mensual()

        for i in range(1,self.meses+1):
            
            interes = CalculadoraPrestamo.interes_cuota(saldo_temp, self.tasa_mensual)
            capital = CalculadoraPrestamo.dividir_pago(cuota, interes)
            saldo_temp=round(saldo_temp-capital,2)

            cursor.execute("""
            INSERT INTO cuotas (prestamo_id,mes,fecha,cuota,interes,capital,saldo,estado)
            VALUES (?,?,?,?,?,?,?,?)
            """,(self.id,i,(self.fecha_inicio+timedelta(days=30*i)).strftime('%Y-%m-%d'),
                 cuota,interes,capital,max(saldo_temp,0),'pendiente'))

        conn.commit()
        self.cargar_cuotas()

    def mostrar_cuotas(self):

        tabla=[]

        for c in self.cuotas:

            estado=c['Estado']

            color_estado=Fore.GREEN if estado=='pagada' else Fore.RED
            color_cuota=Fore.BLUE if estado=='pendiente' else Fore.GREEN

            tabla.append([
                c['Mes'],
                c['Fecha'],
                color_cuota+f"${c['Cuota']:.2f}"+Style.RESET_ALL,
                Fore.RED+f"${c['Interés']:.2f}"+Style.RESET_ALL,
                Fore.CYAN+f"${c['Capital']:.2f}"+Style.RESET_ALL,
                Fore.RED+f"${c['Saldo']:.2f}"+Style.RESET_ALL,
                color_estado+estado+Style.RESET_ALL
            ])

        print("\n"+tabulate(tabla,headers=["Mes","Fecha","Cuota","Interés","Capital","Saldo","Estado"],tablefmt="fancy_grid"))

    def pagar_cuota(self,mes):

        for c in self.cuotas:

            if c['Mes']==mes:

                if c['Estado']=='pagada':
                    print(Fore.RED+"❌ Cuota ya pagada")
                    return

                monto=c['Cuota']
                interes=c['Interés']
                capital=c['Capital']

                self.saldo-=capital

                fecha=datetime.today().strftime("%Y-%m-%d")

                cursor.execute("""
                INSERT INTO abonos (prestamo_id,fecha,monto,interes,capital,saldo_restante)
                VALUES (?,?,?,?,?,?)
                """,(self.id,fecha,monto,interes,capital,max(self.saldo,0)))

                cursor.execute(
                    "UPDATE cuotas SET estado='pagada' WHERE id=?",
                    (c['id'],)
                )

                self.actualizar_saldo_db()
                conn.commit()

                self.cargar_cuotas()
                self.cargar_abonos()

                print(Fore.GREEN+f"✔ Cuota {mes} pagada correctamente")
                return

        print(Fore.RED+"Mes no encontrado")

    def cambiar_estado_cuota(self,mes):
        
        tabla=[]

        for c in self.cuotas:

            estado=c['Estado']

            color_estado=Fore.GREEN if estado=='pagada' else Fore.RED
            color_cuota=Fore.BLUE if estado=='pendiente' else Fore.GREEN

            tabla.append([
                c['Mes'],
                c['Fecha'],
                color_cuota+f"${c['Cuota']:.2f}"+Style.RESET_ALL,
                Fore.YELLOW+f"${c['Interés']:.2f}"+Style.RESET_ALL,
                Fore.CYAN+f"${c['Capital']:.2f}"+Style.RESET_ALL,
                Fore.RED+f"${c['Saldo']:.2f}"+Style.RESET_ALL,
                color_estado+estado+Style.RESET_ALL
            ])

        print("\n"+tabulate(tabla,headers=["Mes","Fecha","Cuota","Interés","Capital","Saldo","Estado"],tablefmt="fancy_grid"))

        for c in self.cuotas:

            if c['Mes']==mes:

                if c['Estado']=="pagada":

                    cursor.execute("""
                    SELECT id,capital FROM abonos
                    WHERE prestamo_id=? AND capital=?
                    ORDER BY id DESC LIMIT 1
                    """,(self.id,c['Capital']))

                    pago=cursor.fetchone()

                    if pago:
                        pago_id,capital=pago

                        cursor.execute("DELETE FROM abonos WHERE id=?",(pago_id,))
                        self.saldo+=capital
                        self.actualizar_saldo_db()

                    cursor.execute(
                        "UPDATE cuotas SET estado='pendiente' WHERE id=?",
                        (c['id'],)
                    )

                    conn.commit()

                    self.cargar_cuotas()
                    self.cargar_abonos()

                    print(Fore.YELLOW+f"✔ Cuota {mes} cambiada a pendiente")
                    
                else:
                    print(Fore.RED+"Use 'Pagar cuota' para registrar el pago")

                return

        print(Fore.RED+"Mes no encontrado")

    def abonar_extra(self,monto):

        if monto<=0:
            print(Fore.RED+"Monto inválido")
            return

        interes = CalculadoraPrestamo.interes_cuota(self.saldo, self.tasa_mensual)

        if monto<=interes:
            interes_pagado=monto
            capital=0
        else:
            interes_pagado=interes
            capital=monto-interes

        self.saldo-=capital

        fecha=datetime.today().strftime("%Y-%m-%d")

        cursor.execute("""
        INSERT INTO abonos (prestamo_id,fecha,monto,interes,capital,saldo_restante)
        VALUES (?,?,?,?,?,?)
        """,(self.id,fecha,monto,interes_pagado,capital,max(self.saldo,0)))

        self.actualizar_saldo_db()

        conn.commit()

        self.cargar_abonos()
        
        print(Fore.MAGENTA + "╔═══════════════════════════════════╗")
        print(Fore.GREEN +  f"║ ✔ Abono registrado:  ${monto:.2f}".ljust(36) + "║")
        print(Fore.YELLOW + f"║ 💰 Interés pagado:   ${interes_pagado:.2f}".ljust(35) + "║")
        print(Fore.CYAN +   f"║ 💰 Capital pagado:   ${capital:.2f}".ljust(35) + "║")
        print(Fore.RED +    f"║ 💰 Saldo restante:   ${self.saldo:.2f}".ljust(35) + "║")
        print(Fore.MAGENTA + "╚═══════════════════════════════════╝")

    def eliminar_abono(self,abono_id):

        cursor.execute(
            "SELECT capital FROM abonos WHERE id=? AND prestamo_id=?",
            (abono_id,self.id)
        )

        abono=cursor.fetchone()

        if not abono:
            print(Fore.RED+"Abono no encontrado")
            return

        capital=abono[0]

        self.saldo+=capital
        self.actualizar_saldo_db()

        cursor.execute(
            "SELECT id FROM cuotas WHERE prestamo_id=? AND capital=? AND estado='pagada'",
            (self.id,capital)
        )

        cuota=cursor.fetchone()

        if cuota:
            cursor.execute(
                "UPDATE cuotas SET estado='pendiente' WHERE id=?",
                (cuota[0],)
            )

        cursor.execute("DELETE FROM abonos WHERE id=?",(abono_id,))
        conn.commit()

        self.cargar_cuotas()
        self.cargar_abonos()

        print(Fore.YELLOW+"Abono eliminado y saldo restaurado")

    def eliminar_prestamo(self):

        confirm=input(Fore.RED+"¿Seguro que desea eliminar este préstamo? (s/n): ")

        if confirm.lower()!="s":
            print("Cancelado")
            return

        cursor.execute("DELETE FROM cuotas WHERE prestamo_id=?", (self.id,))
        cursor.execute("DELETE FROM abonos WHERE prestamo_id=?", (self.id,))
        cursor.execute("DELETE FROM prestamos WHERE id=?", (self.id,))

        conn.commit()

        print(Fore.GREEN+"Préstamo eliminado correctamente")

    def barra_progreso(self):

        pagado=self.monto_inicial-self.saldo
        progreso=pagado/self.monto_inicial

        largo=40
        llenado=int(largo*progreso)

        barra="█"*llenado+"░"*(largo-llenado)
        porcentaje=progreso*100

        print(Fore.CYAN+"\n=========== PROGRESO DEL PRÉSTAMO ===========")
        print(Fore.GREEN+f"Monto inicial : ${self.monto_inicial:.2f}")
        print(Fore.YELLOW+f"Pagado        : ${pagado:.2f}")
        print(Fore.RED+f"Saldo restante: ${self.saldo:.2f}")
       
    # ivitar que pase de 100% por redondeo and saldos negativos
        if porcentaje>100:
            porcentaje=100
        print("\n"+Fore.MAGENTA+f"[{barra}] {porcentaje:.2f}%")
      #si el prestamo está completamente pagado, mostrar mensaje especial
        if porcentaje>=99.99:
            print(Fore.GREEN+"\n🎉 ¡Préstamo completamente pagado! 🎉")

    def mostrar_abonos(self):

        if not self.abonos:
            print(Fore.CYAN+"No hay pagos registrados")
            return

        tabla=[]

        for a in self.abonos:

            tipo_pago="ABONO"

            for c in self.cuotas:
                if abs(a['Monto']-c['Cuota'])<0.01 and abs(a['Interés']-c['Interés'])<0.01:
                    tipo_pago="CUOTA"
                    break

            if tipo_pago=="CUOTA":
                tipo=Fore.BLUE+"CUOTA"+Style.RESET_ALL
            else:
                tipo=Fore.GREEN+"ABONO"+Style.RESET_ALL

            tabla.append([
                a['id'],
                tipo,
                a['Fecha'],
                Fore.BLUE+f"${a['Monto']:.2f}"+Style.RESET_ALL,
                Fore.YELLOW+f"${a['Interés']:.2f}"+Style.RESET_ALL,
                Fore.CYAN+f"${a['Capital']:.2f}"+Style.RESET_ALL,
                Fore.RED+f"${a['Saldo']:.2f}"+Style.RESET_ALL
            ])

        print("\n"+tabulate(tabla,headers=["ID","Tipo","Fecha","Monto","Interés","Capital","Saldo"],tablefmt="fancy_grid"))

def menu_principal():

    while True:

        limpiar_pantalla()

        print(Fore.CYAN + "+-----------------------------------+")
        print(Fore.CYAN + "|       SISTEMA DE PRÉSTAMOS        |")
        print(Fore.CYAN + "+----+------------------------------+")
        print(Fore.GREEN + "| 1  | Crear nuevo préstamo         |")
        print(Fore.CYAN + "+----+------------------------------+")
        print(Fore.GREEN + "| 2  | Cargar préstamos existentes  |")
        print(Fore.CYAN + "+----+------------------------------+")
        print(Fore.GREEN + "| 3  | Salir                        |")
        print(Fore.CYAN + "+----+------------------------------+")

        op = input(Fore.YELLOW + "| Seleccione una opción: ")

        if op == "1":

            while True:
                try:
                    print(Fore.CYAN + "+-----------------------------------+")
                    monto = float(input(Fore.YELLOW + "| Ingrese monto solicitado: "))
                    if monto <= 0:
                        print(Fore.RED + "| ❌ El monto debe ser mayor que 0      |")
                        continue
                    break
                except ValueError:
                    print(Fore.CYAN + "+-----------------------------------+")
                    print(Fore.RED + "|    ❌ Ingrese un número válido    |")

            while True:
                try:
                    print(Fore.CYAN + "+-----------------------------------+")
                    meses = int(input(Fore.YELLOW + "| Ingrese meses a pagar: "))
                    print(Fore.CYAN + "+-----------------------------------+")
                    if meses <= 0:
                        print(Fore.RED + "| ❌ Los meses deben ser mayores que 0  |")
                        continue
                    break
                except ValueError:
                    print(Fore.CYAN + "+-----------------------------------+")
                    print(Fore.RED + "|    ❌ Ingrese un número entero válido    |")
            limpiar_pantalla()
            prestamo = PrestamoColor(monto=monto, meses=meses)
            menu_prestamo(prestamo)

        elif op == "2":

            limpiar_pantalla()

            cursor.execute("SELECT id, monto_inicial, saldo FROM prestamos")
            prestamos = cursor.fetchall()

            if not prestamos:
                print(Fore.RED + "+---------------------------------+")
                print(Fore.RED + "| ❌ No hay préstamos registrados |")
                print(Fore.RED + "+---------------------------------+")
                input(Fore.YELLOW + "| Presione Enter para continuar... ")
                continue

            print(Fore.RED + "+-----------------------------------+")
            print(Fore.CYAN + "|       PRÉSTAMOS EXISTENTES        |")
            print(Fore.RED + "+-----------------------------------+")

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
                    pid = int(input(Fore.YELLOW + "| Ingrese ID del préstamo: "))
                    print(Fore.YELLOW + "+--------------------------+")
                    break
                except ValueError:
                    print(Fore.RED + "+-----------------------------------+")
                    print(Fore.RED + "|     ❌ Debe ingresar un número    |")
                    print(Fore.RED + "+-----------------------------------+")

            cursor.execute("SELECT id FROM prestamos WHERE id=?", (pid,))
            existe = cursor.fetchone()

            if not existe:
                print(Fore.RED + "+---------------------------+")
                print(Fore.RED + "| ❌ Ese préstamo no existe |")
                print(Fore.RED + "+---------------------------+")
                input(Fore.YELLOW + "| Presione Enter para continuar... ")
                continue

            prestamo = PrestamoColor(prestamo_id=pid)
            menu_prestamo(prestamo)

        elif op == "3":

            print(Fore.GREEN + "+-----------------------------------+")
            print(Fore.GREEN + "|    Gracias por usar el sistema    |")
            print(Fore.GREEN + "+-----------------------------------+")
            break

        else:

            print(Fore.RED + "+-----------------------------------+")
            print(Fore.RED + "|        ❌ Opción inválida         |")
            print(Fore.RED + "+-----------------------------------+")
            input(Fore.YELLOW + "| Presione Enter para continuar... ")
    

def menu_prestamo(prestamo):

    while True:

        limpiar_pantalla()

        print(Fore.CYAN + "\n+---------------------------+")
        print(Fore.CYAN + "|       MENÚ PRÉSTAMO       |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 1  | Ver cuotas           |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 2  | Pagar cuota          |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 3  | Abono extra          |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 4  | Historial pagos      |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 5  | Progreso préstamo    |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 6  | Cambiar estado cuota |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 7  | Eliminar abono       |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 8  | Resumen financiero   |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 9  | Eliminar préstamo    |")
        print(Fore.CYAN + "+----+----------------------+")
        print(Fore.GREEN + "| 10 | Volver               |")
        print(Fore.CYAN + "+----+----------------------+")

        op = input(Fore.YELLOW + "| Seleccione una opción: ")

        # VER CUOTAS
        if op == "1":

            limpiar_pantalla()
            prestamo.mostrar_cuotas()
            pausa()

       # PAGAR CUOTA
        elif op == "2":

            limpiar_pantalla()

            print(Fore.CYAN + "+-------------------------+")
            print(Fore.CYAN + "|        PAGAR CUOTA      |")
            print(Fore.CYAN + "+-------------------------+")

            prestamo.mostrar_cuotas()

            try:
                mes = int(input(Fore.GREEN + "\n| Número de cuota a pagar: "))
                prestamo.pagar_cuota(mes)
            except:
                print(Fore.RED + "❌ Entrada inválida")

            pausa()
        # ABONO EXTRA
        elif op == "3":

            limpiar_pantalla()

            print(Fore.CYAN + "+-----------------------+")
            print(Fore.CYAN + "|      ABONO EXTRA      |")
            print(Fore.CYAN + "+-----------------------+")

            try:
                print(Fore.GREEN + "+=======================+")
                monto = float(input(Fore.YELLOW + "| Monto a abonar: "))
                print(Fore.GREEN + "+=======================+")
                prestamo.abonar_extra(monto)
            except:
                print(Fore.RED + "❌ Entrada inválida")

            pausa()

        # HISTORIAL
        elif op == "4":

            limpiar_pantalla()
            prestamo.mostrar_abonos()
            pausa()

        # PROGRESO
        elif op == "5":

            limpiar_pantalla()
            prestamo.barra_progreso()
            pausa()

        # CAMBIAR ESTADO
        elif op == "6":

            limpiar_pantalla()

            print(Fore.CYAN + "+--------------------------+")
            print(Fore.CYAN + "|   CAMBIAR ESTADO CUOTA   |")
            print(Fore.CYAN + "+--------------------------+")

            try:
                mes = int(input(Fore.YELLOW + "| Número de cuota: "))
                prestamo.cambiar_estado_cuota(mes)
            except:
                print(Fore.RED + "❌ Entrada inválida")

            pausa()

        # ELIMINAR ABONO
        elif op == "7":

            limpiar_pantalla()

            prestamo.mostrar_abonos()

            print(Fore.CYAN + "\n+------------------------+")
            print(Fore.CYAN + "|     ELIMINAR ABONO     |")
            print(Fore.CYAN + "+------------------------+")

            try:
                abono_id = int(input(Fore.YELLOW + "| ID del abono: "))
                prestamo.eliminar_abono(abono_id)
            except:
                print(Fore.RED + "❌ Entrada inválida")

            pausa()

        # RESUMEN
        elif op == "8":

            limpiar_pantalla()
            prestamo.resumen_financiero()
            pausa()

        # ELIMINAR PRESTAMO
        elif op == "9":

            limpiar_pantalla()

            print(Fore.RED + "+------------------------+")
            print(Fore.RED + "|   ELIMINAR PRÉSTAMO    |")
            print(Fore.RED + "+------------------------+")

            confirm = input(Fore.YELLOW + "| ¿Seguro? (s/n): ")

            if confirm.lower() == "s":
                prestamo.eliminar_prestamo()
                pausa()
                break

        # VOLVER
        elif op == "10":
            break

        else:
            print(Fore.RED + "+---------------------------+")
            print(Fore.RED + "|    ❌ Opción inválida     |")
            print(Fore.RED + "+---------------------------+")
            pausa()


pantalla_inicio()
menu_principal()