import sqlite3
from datetime import datetime, timedelta
from tabulate import tabulate
from colorama import Fore, Style, init
import os
import time

def pausa():
    input(Fore.YELLOW + "\n╔═══════════════════════════╗\n"
          "║ Press. ENTER For continue ║\n"
          "╚═══════════════════════════╝")

def limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")


def pantalla_inicio():

    limpiar_pantalla()

    print(Fore.CYAN + """
╔══════════════════════╗
║ SISTEMA DE PRÉSTAMOS ║
╚══════════════════════╝
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

            self.interes_pagado = 0

            self.fecha_inicio = datetime.strptime(fecha, "%Y-%m-%d")

        # CREAR NUEVO PRÉSTAMO
        else:

            # El monto inicial debe ser solo el dinero prestado
            self.monto_inicial = monto
            self.saldo = monto
            self.meses = meses
            self.monto = monto   # importante para cálculos
            self.fecha_inicio = datetime.today()

            cursor.execute("""
            INSERT INTO prestamos (monto_inicial, saldo, meses, tasa, fecha_inicio)
            VALUES (?,?,?,?,?)
            """,(
                self.monto_inicial,
                self.saldo,
                self.meses,
                self.tasa_mensual,
                self.fecha_inicio.strftime("%Y-%m-%d")
            ))

            conn.commit()
            self.id = cursor.lastrowid

        self.cargar_cuotas()

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

        interes_restante = total_interes - (total_interes * (capital_pagado / self.monto_inicial))

        if interes_restante < 0:
            interes_restante = 0

        return round(interes_restante,2)


    def resumen_financiero(self):

        pagado=self.monto_inicial-self.saldo
        progreso=pagado/self.monto_inicial
        cuota = self.cuota_mensual()
        total = self.total_a_pagar()
        interes_total = self.interes_total_prestamo()
        interes_restante = self.interes_restante()
        interes=interes_total-interes_restante
        
        largo=35
        llenado=int(largo*progreso)

        barra="█"*llenado+"░"*(largo-llenado)
        porcentaje=progreso*100

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

        # Evitar que pase de 100% por redondeo and saldos negativos
        if porcentaje>100:
            porcentaje=100
        print("\n"+Fore.MAGENTA+f"[{barra}] {porcentaje:.2f}%")
      #si el prestamo está completamente pagado, mostrar mensaje especial
        if porcentaje>=99.99:
            print(Fore.GREEN+"\n🎉 ¡Préstamo completamente pagado! 🎉")

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
                    print(Fore.CYAN + "╔══════════════════════╗")
                    print(Fore.RED+f"║ ❌ Cuota {mes} ya pagada ║")
                    print(Fore.CYAN + "╚══════════════════════╝")
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

                print(Fore.MAGENTA+"╔════════════════════════════════╗")
                print(Fore.GREEN+f"║ ✔ Cuota {mes} pagada correctamente ║")
                print(Fore.MAGENTA+"╚════════════════════════════════╝")
                return

        print(Fore.MAGENTA+"╔══════════════════════╗")
        print(Fore.RED+"║ ❌ Mes no encontrado ║")
        print(Fore.MAGENTA+"╚══════════════════════╝")

    def cambiar_estado_cuota(self,mes):

        for c in self.cuotas:

            if c['Mes']==mes:

                if c['Estado']=="pagada":

                    cursor.execute("""
                    SELECT id,capital FROM abonos
                    WHERE prestamo_id=? AND ABS(capital-?)<0.01
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

                    print(Fore.CYAN + "╔════════════════════════════════╗")
                    print(Fore.YELLOW+f"║ ✔ Cuota {mes} cambiada a pendiente ║")
                    print(Fore.CYAN + "╚════════════════════════════════╝")
                    
                else:
                    print(Fore.CYAN + "╔══════════════════════════════════════════╗")
                    print(Fore.RED+"║ Use 'Pagar cuota' para registrar el pago ║")
                    print(Fore.CYAN + "╚══════════════════════════════════════════╝")
                return

        print(Fore.MAGENTA+"╔══════════════════════╗")
        print(Fore.RED+"║ ❌ Mes no encontrado ║")
        print(Fore.MAGENTA+"╚══════════════════════╝")

    def eliminar_prestamo(self):
        print(Fore.CYAN+"+==============================================================+")
        confirm=input(Fore.RED+" |¿Seguro que desea eliminar este préstamo? (S/N): S=SI / N=NO | ")
     
        print(Fore.CYAN+"+==============================================================+")

        if confirm.upper()!="S":
            print(Fore.CYAN+"+==========================+")
            print(Fore.RED+"| Cancelado por el usuario |")
            print(Fore.CYAN+"+==========================+")
            return

        cursor.execute("DELETE FROM cuotas WHERE prestamo_id=?", (self.id,))
        cursor.execute("DELETE FROM abonos WHERE prestamo_id=?", (self.id,))
        cursor.execute("DELETE FROM prestamos WHERE id=?", (self.id,))

        conn.commit()
        print(Fore.CYAN+"+================================+")
        print(Fore.GREEN+"|Préstamo eliminado correctamente|")
        print(Fore.CYAN+"+================================+")

def menu_principal():

    while True:

        limpiar_pantalla()

        print(Fore.RED + "╔══════════════════════╗")
        print(Fore.RED + "║ SISTEMA DE PRÉSTAMOS ║")
        print(Fore.RED + "╚══════════════════════╝") 
        print(Fore.CYAN + "╔═══╗══════════════════╗")
        print(Fore.GREEN +"║ 1 ║  Crear préstamo  ║")
        print(Fore.CYAN + "╚═══╝══════════════════╝")
        print(Fore.CYAN + "╔═══╗══════════════════╗")
        print(Fore.GREEN +"║ 2 ║ Cargar préstamos ║")
        print(Fore.CYAN + "╚═══╝══════════════════╝")
        print(Fore.CYAN + "╔═══╗══════════════════╗")
        print(Fore.GREEN +"║ 3 ║ Salir            ║")
        print(Fore.CYAN + "╚═══╝══════════════════╝")
        
        print(Fore.CYAN + "╔══════════════════════╗")
        op = input(Fore.YELLOW +"║Seleccione una opción:║ ")
        print(Fore.CYAN + "╚══════════════════════╝")

        if op == "1":

    # INGRESAR MONTO
            limpiar_pantalla()
            while True:
                try:
                    print(Fore.CYAN + "╔══════════════════════════╗")
                    print(Fore.CYAN + "║      NUEVO PRÉSTAMO      ║")
                    print(Fore.CYAN + "╠══════════════════════════╣")

                    monto = float(input(Fore.YELLOW + "║ Ingrese monto solicitado: "))

                    if monto <= 0:
                        print(Fore.RED + "╠══════════════════════════╣")
                        print(Fore.RED + "║❌ El monto debe ser >0║")
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
                        print(Fore.RED + "║ ❌ Meses deben ser > 0   ║")
                        print(Fore.RED + "╠══════════════════════════╣")
                        continue

                    print(Fore.CYAN + "╠══════════════════════════╣")
                    break

                except ValueError:
                    print(Fore.RED + "╠══════════════════════════╣")
                    print(Fore.RED + "║❌ Número entero inválido ║")
                    print(Fore.RED + "╠══════════════════════════╣")


            limpiar_pantalla()

            prestamo = PrestamoColor(monto=monto, meses=meses)

            menu_prestamo(prestamo)

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
                    print(Fore.RED + "║     ❌ Debe ingresar un número    ║")
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

        elif op == "3":

            print(Fore.MAGENTA + "╔══════════════════════╗")
            print(Fore.GREEN + "║ Gracias Hasta Luego  ║")
            print(Fore.MAGENTA + "╚══════════════════════╝")
            break

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
        print(Fore.GREEN + "║ 4  ║ Historial pagos      ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 5  ║ Cambiar estado cuota ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 7  ║ Resumen financiero   ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 8  ║ Eliminar préstamo    ║")
        print(Fore.CYAN + "╠════╬══════════════════════╣")
        print(Fore.GREEN + "║ 9  ║ Volver               ║")
        print(Fore.CYAN + "╚════╩══════════════════════╝")

        op = input(Fore.YELLOW + "║ Seleccione una opción: ")

        # VER CUOTAS
        if op == "1":

            limpiar_pantalla()

            print(Fore.CYAN + "╔════════════╗")
            print(Fore.CYAN + "║ VER CUOTAS ║")
            print(Fore.CYAN + "╚════════════╝")
            prestamo.mostrar_cuotas()

            pausa()
       # PAGAR CUOTA
        elif op == "2":

            limpiar_pantalla()

            print(Fore.CYAN + "╔═════════════╗")
            print(Fore.CYAN + "║ PAGAR CUOTA ║")
            print(Fore.CYAN + "╚═════════════╝")

            prestamo.mostrar_cuotas()

            try:
                print(Fore.RED + "╔═════════════════════════╗")
                mes = int(input(Fore.GREEN + "║ Número de cuota a pagar:║"))
                print(Fore.RED + "╚═════════════════════════╝")
                prestamo.pagar_cuota(mes)
            except:
                print(Fore.RED + "╔════════════════════╗")
                print(Fore.RED + "║❌ Entrada inválida ║")
                print(Fore.RED + "╚════════════════════╝")

            pausa()
       
       # HISTORIAL
        elif op == "4":

            limpiar_pantalla()

            print(Fore.CYAN + "╔════════════════════╗")
            print(Fore.CYAN + "║ HISTORIAL DE CUOTAS ║")
            print(Fore.CYAN + "╚════════════════════╝")
        
        # CAMBIAR ESTADO CUOTA
        elif op == "5":

            limpiar_pantalla()

            print(Fore.CYAN + "╔══════════════════════╗")
            print(Fore.CYAN + "║ CAMBIAR ESTADO CUOTA ║")
            print(Fore.CYAN + "╚══════════════════════╝")

            # MOSTRAR TABLA DE CUOTAS
            prestamo.mostrar_cuotas()

            try:
                mes = int(input(Fore.YELLOW + "| Número de cuota a modificar: "))

                prestamo.cambiar_estado_cuota(mes)

                # 🔄 MOSTRAR TABLA ACTUALIZADA
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

       # RESUMEN FINANCIERO
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


        # VOLVER
        elif op == "9":

            limpiar_pantalla()

            print(Fore.CYAN + "╔═══════════════════════════╗")
            print(Fore.CYAN + "║VOLVIENDO AL MENÚ PRINCIPAL║")
            print(Fore.CYAN + "╚═══════════════════════════╝")

            pausa()
            break


        # OPCIÓN INVÁLIDA
        else:

            print(Fore.RED + "╔═══════════════════════════╗")
            print(Fore.RED + "║     ❌ OPCIÓN INVÁLIDA    ║")
            print(Fore.RED + "╚═══════════════════════════╝")

            pausa()


pantalla_inicio()
menu_principal()