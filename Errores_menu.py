import sqlite3
from datetime import datetime, timedelta
from tabulate import tabulate
from colorama import Fore, Style, init

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
            self.fecha_inicio = datetime.strptime(fecha, "%Y-%m-%d")

        else:

            self.monto_inicial = monto
            self.saldo = monto
            self.meses = meses
            self.fecha_inicio = datetime.today()

            cursor.execute("""
            INSERT INTO prestamos (monto_inicial, saldo, meses, tasa, fecha_inicio)
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

    def generar_cuotas(self):

        saldo_temp=self.monto_inicial
        cuota=self.cuota_mensual()

        for i in range(1,self.meses+1):

            interes=round(saldo_temp*self.tasa_mensual,2)
            capital=round(cuota-interes,2)
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
                Fore.YELLOW+f"${c['Interés']:.2f}"+Style.RESET_ALL,
                Fore.CYAN+f"${c['Capital']:.2f}"+Style.RESET_ALL,
                Fore.RED+f"${c['Saldo']:.2f}"+Style.RESET_ALL,
                color_estado+estado+Style.RESET_ALL
            ])

        print("\n"+tabulate(tabla,headers=["Mes","Fecha","Cuota","Interés","Capital","Saldo","Estado"],tablefmt="fancy_grid"))

    def pagar_cuota(self,mes):

        for c in self.cuotas:

            if c['Mes']==mes:

                if c['Estado']=='pagada':
                    print(Fore.YELLOW+"Cuota ya pagada")
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

                print(Fore.GREEN+f"Cuota {mes} pagada correctamente")
                return

        print(Fore.RED+"Mes no encontrado")

    def cambiar_estado_cuota(self,mes):

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

                    print(Fore.YELLOW+"Cuota cambiada a pendiente")

                else:
                    print(Fore.RED+"Use 'Pagar cuota' para registrar el pago")

                return

        print(Fore.RED+"Mes no encontrado")

    def abonar_extra(self,monto):

        if monto<=0:
            print(Fore.RED+"Monto inválido")
            return

        interes=round(self.saldo*self.tasa_mensual,2)

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

        print(Fore.GREEN+" 💰Abono registrado")
        print(Fore.YELLOW+f"💰Interés pagado: ${interes_pagado:.2f}")
        print(Fore.CYAN+f"💰Capital pagado: ${capital:.2f}")
        print(Fore.RED+f"💰Saldo restante: ${self.saldo:.2f}")

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
        print("\n"+Fore.MAGENTA+f"[{barra}] {porcentaje:.2f}%")



def menu_principal():

    while True:

        print(Fore.CYAN+"\n=== SISTEMA DE PRÉSTAMOS ===")
        print("1 Crear préstamo")
        print("2 Cargar préstamo")
        print("3 Salir")

        op=input("Seleccione: ")

        if op=="1":

            monto=float(input("Monto: "))
            meses=int(input("Meses: "))

            prestamo=PrestamoColor(monto=monto,meses=meses)
            menu_prestamo(prestamo)

        elif op=="2":

            cursor.execute("SELECT id,monto_inicial,saldo FROM prestamos")
            prestamos=cursor.fetchall()

            if not prestamos:
                print("No hay préstamos")
                continue

            for p in prestamos:
                print(f"ID {p[0]} | Inicial ${p[1]:.2f} | Saldo ${p[2]:.2f}")

            pid=int(input("ID préstamo: "))
            prestamo=PrestamoColor(prestamo_id=pid)

            menu_prestamo(prestamo)

        elif op=="3":
            break


def menu_prestamo(prestamo):

    while True:

        print(Fore.CYAN+"\n--- MENÚ PRÉSTAMO ---")

        print("1 Ver cuotas")
        print("2 Pagar cuota")
        print("3 Abono extra")
        print("4 Historial pagos")
        print("5 Progreso préstamo")
        print("6 Cambiar estado cuota")
        print("7 Eliminar abono")
        print("8 Eliminar préstamo")
        print("9 Volver")

        op=input("Seleccione: ")

        if op=="1":
            prestamo.mostrar_cuotas()

        elif op=="2":
            mes=int(input("Número de cuota: "))
            prestamo.pagar_cuota(mes)

        elif op=="3":
            monto=float(input("Monto abono: "))
            prestamo.abonar_extra(monto)

        elif op=="5":
            prestamo.barra_progreso()

        elif op=="7":
            abono_id=int(input("ID del abono a eliminar: "))
            prestamo.eliminar_abono(abono_id)

        elif op=="8":
            prestamo.eliminar_prestamo()
            break

        elif op=="9":
            break


menu_principal()

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