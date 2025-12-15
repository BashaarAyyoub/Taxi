import math
import random
import threading

from config import (
    DAY_MINUTES,
    TRIP_MIN, TRIP_MODE, TRIP_MAX,
    WAIT_MIN, WAIT_MODE, WAIT_MAX,
    RETRY_MIN, RETRY_MODE, RETRY_MAX,
)
from sistema import Sistema


class Cliente(threading.Thread):
    """
    Cliente persistente:
    - Puede iniciar viajes mientras hora < 24:00
    - Si un viaje se pasa de 24:00, se termina igual
    - Entre viajes espera un tiempo aleatorio razonable
    """
    def __init__(self, sistema: Sistema, client_id: int):
        super().__init__(daemon=True)
        self.sistema = sistema
        self.client_id = client_id

    def run(self):
        #desfase inicial suave para que no arranquen todos a la vez
        self.sistema.sleep_minutes(random.randint(0, 10))

        while True:
            now = self.sistema.now_minute()
            if now >= DAY_MINUTES or self.sistema.is_day_finished():
                break  #no iniciar viajes nuevos tras terminar el día

            ox, oy = self.sistema.rand_point()
            dx, dy = self.sistema.rand_point()
            distance = math.dist((ox, oy), (dx, dy))

            taxi = self.sistema.assign_taxi(self.client_id, ox, oy)
            if taxi is None:
                retry = max(1, self.sistema.tri_int(RETRY_MIN, RETRY_MODE, RETRY_MAX))
                self.sistema.sleep_minutes(retry)
                continue

            start = self.sistema.now_minute()
            duration = max(1, self.sistema.tri_int(TRIP_MIN, TRIP_MODE, TRIP_MAX))
            end = start + duration  #puede pasar de 24:00

            self.sistema.begin_service()

            #imprimir inicio + estado taxis
            self.sistema.sem_print.acquire()
            try:
                libres, ocupados = self.sistema.taxi_status_snapshot()
                print(f"\nTaxi-{taxi.id} inicia servicio con Cliente-{self.client_id}")
                print(f"Hora inicio: {self.sistema.minute_to_clock(start)}")
                print(f"Hora fin prevista: {self.sistema.minute_to_clock(end)}")
                print(f"Origen: ({ox:.2f}, {oy:.2f}) → Destino: ({dx:.2f}, {dy:.2f})")
                print(f"Distancia: {distance:.2f} km | Duración: {duration} min")
                print("Taxis libres:", ", ".join(libres) if libres else "Ninguno")
                print("Taxis ocupados:", ", ".join(ocupados) if ocupados else "Ninguno")
                print("-" * 70)
            finally:
                self.sistema.sem_print.release()

            #simular el viaje
            self.sistema.sleep_minutes(duration)

            #finalizar y actualizar
            rating = random.randint(1, 5)
            fare = self.sistema.compute_fare(distance)
            self.sistema.finish_trip(taxi, dx, dy, fare, rating)
            self.sistema.end_service()

            #imprimir fin + estado taxis
            self.sistema.sem_print.acquire()
            try:
                libres, ocupados = self.sistema.taxi_status_snapshot()
                print(f"Servicio finalizado | Cliente-{self.client_id} → Taxi-{taxi.id}")
                print(f"Hora fin real: {self.sistema.minute_to_clock(end)}")
                print(f"Coste: {fare:.2f} € | Rating: {rating}")
                print("Taxis libres:", ", ".join(libres) if libres else "Ninguno")
                print("Taxis ocupados:", ", ".join(ocupados) if ocupados else "Ninguno")
                print("-" * 70)
            finally:
                self.sistema.sem_print.release()

            #espera razonable antes del siguiente viaje
            wait = max(1, self.sistema.tri_int(WAIT_MIN, WAIT_MODE, WAIT_MAX))
            self.sistema.sleep_minutes(wait)
