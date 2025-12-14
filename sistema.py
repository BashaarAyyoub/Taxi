# sistema.py
import math
import random
import threading
import time
from typing import List, Optional, Tuple

from config import (
    SIM_MINUTE_SECONDS, DAY_MINUTES,
    MAP_MIN, MAP_MAX,
    SEARCH_RADIUS_KM,
    BASE_FEE_EUR, EUR_PER_KM_MIN, EUR_PER_KM_MAX,
)
from models import Taxi


class Sistema:
    """
    Sistema central UNIETAXI.
    Solo usa semáforos binarios (Semaphore(1)) para proteger recursos críticos.
    """
    def __init__(self, taxis: List[Taxi]):
        self.taxis = taxis

        # Semáforos binarios (PDF)
        self.sem_taxis = threading.Semaphore(1)
        self.sem_clock = threading.Semaphore(1)
        self.sem_services = threading.Semaphore(1)
        self.sem_print = threading.Semaphore(1)

        # Reloj simulado
        self.current_minute = 0
        self.day_finished = False

        # Servicios activos
        self.services_active = 0

    # ---------- Tiempo ----------
    def sleep_minutes(self, minutes: int) -> None:
        time.sleep(minutes * SIM_MINUTE_SECONDS)

    def now_minute(self) -> int:
        self.sem_clock.acquire()
        try:
            return self.current_minute
        finally:
            self.sem_clock.release()

    def is_day_finished(self) -> bool:
        self.sem_clock.acquire()
        try:
            return self.day_finished
        finally:
            self.sem_clock.release()

    def clock_loop(self) -> None:
        """
        Reloj: avanza de 00:00 a 24:00 (1440 min). A 24:00 se cierra la jornada.
        """
        while True:
            self.sleep_minutes(1)
            self.sem_clock.acquire()
            try:
                if self.current_minute >= DAY_MINUTES:
                    self.day_finished = True
                    break
                self.current_minute += 1
            finally:
                self.sem_clock.release()

    # ---------- Formato hora ----------
    @staticmethod
    def minute_to_clock(m: int) -> str:
        day_offset = m // DAY_MINUTES
        mm = m % DAY_MINUTES
        hh = mm // 60
        mi = mm % 60
        if day_offset <= 0:
            return f"{hh:02d}:{mi:02d}"
        return f"{hh:02d}:{mi:02d} (+{day_offset}d)"

    # ---------- Servicios activos ----------
    def begin_service(self) -> None:
        self.sem_services.acquire()
        try:
            self.services_active += 1
        finally:
            self.sem_services.release()

    def end_service(self) -> None:
        self.sem_services.acquire()
        try:
            self.services_active -= 1
        finally:
            self.sem_services.release()

    def active_services(self) -> int:
        self.sem_services.acquire()
        try:
            return self.services_active
        finally:
            self.sem_services.release()

    # ---------- Estado taxis ----------
    def taxi_status_snapshot(self) -> Tuple[List[str], List[str]]:
        self.sem_taxis.acquire()
        try:
            libres = [f"Taxi-{t.id}" for t in self.taxis if t.free]
            ocupados = []
            for t in self.taxis:
                if not t.free:
                    if t.current_client_id is None:
                        ocupados.append(f"Taxi-{t.id}")
                    else:
                        ocupados.append(f"Taxi-{t.id}(Cliente-{t.current_client_id})")
            return libres, ocupados
        finally:
            self.sem_taxis.release()

    # ---------- Asignación ----------
    def assign_taxi(self, client_id: int, ox: float, oy: float) -> Optional[Taxi]:
        """
        Selección en radio 2 km:
        - más cercano
        - empate -> mejor rating medio
        """
        self.sem_taxis.acquire()
        try:
            candidates = []
            for t in self.taxis:
                if not t.free:
                    continue
                d = math.dist((ox, oy), (t.x, t.y))
                if d <= SEARCH_RADIUS_KM:
                    candidates.append((round(d, 6), -t.rating_avg, t.id, t))

            if not candidates:
                return None

            candidates.sort()
            chosen = candidates[0][3]
            chosen.free = False
            chosen.current_client_id = client_id
            return chosen
        finally:
            self.sem_taxis.release()

    # ---------- Actualización taxi tras viaje ----------
    def finish_trip(self, taxi: Taxi, dx: float, dy: float, fare: float, rating: int) -> None:
        """
        Marca libre, acumula stats y mueve el taxi al destino (realismo + reparto).
        """
        self.sem_taxis.acquire()
        try:
            taxi.free = True
            taxi.current_client_id = None
            taxi.services += 1
            taxi.earnings += fare
            taxi.rating_sum += rating
            taxi.rating_count += 1

            # Mover al destino
            taxi.x = dx
            taxi.y = dy
        finally:
            self.sem_taxis.release()

    # ---------- Aleatorios ----------
    @staticmethod
    def tri_int(a: int, mode: int, b: int) -> int:
        # Triangular: la mayoría cae cerca de mode, pero con variabilidad
        return int(round(random.triangular(a, b, mode)))

    @staticmethod
    def rand_point() -> Tuple[float, float]:
        return random.uniform(MAP_MIN, MAP_MAX), random.uniform(MAP_MIN, MAP_MAX)

    @staticmethod
    def compute_fare(distance_km: float) -> float:
        eur_km = random.uniform(EUR_PER_KM_MIN, EUR_PER_KM_MAX)
        return round(BASE_FEE_EUR + distance_km * eur_km, 2)

