# main.py
import random
import threading
import time

from config import MAP_MIN, MAP_MAX
from models import Taxi
from sistema import Sistema
from cliente import Cliente


def read_positive_int(prompt: str) -> int:
    while True:
        try:
            v = int(input(prompt).strip())
            if v > 0:
                return v
        except ValueError:
            pass
        print("Introduce un entero positivo.")


def resumen_final(sistema: Sistema):
    # snapshot seguro de taxis
    sistema.sem_taxis.acquire()
    try:
        taxis = list(sistema.taxis)
    finally:
        sistema.sem_taxis.release()

    print("\n" + "=" * 50)
    print("RESUMEN FINAL DEL DÍA")
    print("=" * 50)

    top_g = None
    top_r = None

    for t in taxis:
        print(
            f"Taxi-{t.id} | Servicios: {t.services} | "
            f"Ganancias: {t.earnings:.2f} € | "
            f"Rating medio: {t.rating_avg:.2f}"
        )

        if top_g is None or t.earnings > top_g.earnings:
            top_g = t
        if top_r is None or t.rating_avg > top_r.rating_avg:
            top_r = t

    if top_g:
        print(f"\n🏆 Taxi con más ganancias: Taxi-{top_g.id}")
    if top_r:
        print(f"⭐ Taxi mejor valorado: Taxi-{top_r.id} ({top_r.rating_avg:.2f})")


def main():
    n_taxis = read_positive_int("Ingrese número de taxis: ")
    n_clients = read_positive_int("Ingrese número de clientes: ")

    taxis = [
        Taxi(id=i + 1, x=random.uniform(MAP_MIN, MAP_MAX), y=random.uniform(MAP_MIN, MAP_MAX))
        for i in range(n_taxis)
    ]

    sistema = Sistema(taxis)

    # Reloj 24h
    clock = threading.Thread(target=sistema.clock_loop)
    clock.start()

    # Clientes persistentes
    clients = [Cliente(sistema, client_id=i + 1) for i in range(n_clients)]

    for c in clients:
        c.start()

    # Esperar fin del día + servicios activos == 0
    while True:
        finished = sistema.is_day_finished()
        active = sistema.active_services()
        if finished and active == 0:
            break
        time.sleep(0.1)

    resumen_final(sistema)


if __name__ == "__main__":
    main()
