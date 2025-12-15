import math                 #para calcular distancia euclídea
import random               #para aleatoriedad
import threading            #para semáforos binarios
import time                 #para sleep real

from typing import List, Optional, Tuple  #tipos para claridad

from config import (        #parámetros de configuración
    SIM_MINUTE_SECONDS,
    DAY_MINUTES,
    MAP_MIN,
    MAP_MAX,
    SEARCH_RADIUS_KM,
    BASE_FEE_EUR,
    EUR_PER_KM_MIN,
    EUR_PER_KM_MAX,
)

from models import Taxi     #modelo taxi


class Sistema:
    """
    Recursos importantes:
    - Lista/estado de taxis
    - Reloj global
    - Contador de servicios activos
    - Salida por consola (para que no se mezcle)
    Se protege todo con semáforos binarios: threading.Semaphore(1)
    """

    def __init__(self, taxis: List[Taxi]):
        
        self.taxis = taxis

        
        #SEMÁFOROS BINARIOS
        self.sem_taxis = threading.Semaphore(1)     #protege datos de taxis 
        self.sem_clock = threading.Semaphore(1)     #protege current_minute y day_finished
        self.sem_services = threading.Semaphore(1)  #protege services_active
        self.sem_print = threading.Semaphore(1)     #protege prints para que no se solapen

      
       
        #RELOJ
        self.current_minute = 0      
        self.day_finished = False    

        
        #SERVICIOS ACTIVOS
        self.services_active = 0     #cuántos servicios están ocurriendo ahora mismo

    def sleep_minutes(self, minutes: int) -> None:
        #convierte minutos simulados a segundos reales y duerme
        time.sleep(minutes * SIM_MINUTE_SECONDS)

    def now_minute(self) -> int:
        #lee el minuto actual protegido por sem_clock
        self.sem_clock.acquire()
        try:
            return self.current_minute
        finally:
            self.sem_clock.release()

    def is_day_finished(self) -> bool:
        #lee la bandera day_finished protegida por sem_clock.
        self.sem_clock.acquire()
        try:
            return self.day_finished
        finally:
            self.sem_clock.release()

    def clock_loop(self) -> None:
        """
        Reloj del sistema:
        avanza minuto a minuto
        cuando llega a 24:00 (1440), marca day_finished=True
        """
        while True:
            #espera 1 minuto simulado
            self.sleep_minutes(1)

            #wntra en sección crítica del reloj
            self.sem_clock.acquire()
            try:
                #si ya llegamos al final del día, cerramos el reloj
                if self.current_minute >= DAY_MINUTES:
                    self.day_finished = True
                    break

                #avanzamos el tiempo
                self.current_minute += 1
            finally:
                #salimos de sección crítica del reloj
                self.sem_clock.release()

    
    @staticmethod
    def minute_to_clock(m: int) -> str:
        """
        Convierte un minuto absoluto a HH:MM.
        Si pasa de 24:00, lo marca como (+1d), (+2d), etc.
        """
        day_offset = m // DAY_MINUTES          #cuántos días se ha pasado.
        mm = m % DAY_MINUTES                   #minuto dentro del día.
        hh = mm // 60                          #hora.
        mi = mm % 60                           #minuto.

        # Si no se ha pasado de día, mostramos normal.
        if day_offset <= 0:
            return f"{hh:02d}:{mi:02d}"

        # Si se ha pasado, indicamos +1d, +2d...
        return f"{hh:02d}:{mi:02d} (+{day_offset}d)"

    
    def begin_service(self) -> None:
        #ncirementa services_active en sección crítica
        self.sem_services.acquire()
        try:
            self.services_active += 1
        finally:
            self.sem_services.release()

    def end_service(self) -> None:
        #decrementa services_active en sección crítica
        self.sem_services.acquire()
        try:
            self.services_active -= 1
        finally:
            self.sem_services.release()
        #estado de servicios activos
    def active_services(self) -> int:
      
        self.sem_services.acquire()
        try:
            return self.services_active
        finally:
            self.sem_services.release()

        #estado de taxis
    def taxi_status_snapshot(self) -> Tuple[List[str], List[str]]:
        """
        Devuelve (libres, ocupados) como listas de strings para imprimir.
        Se protege con sem_taxis porque lee estados compartidos.
        """
        self.sem_taxis.acquire()
        try:
            libres = []    #lista de taxis libres
            ocupados = []  #lista de taxis ocupados

            #recorremos taxis y clasificamos
            for t in self.taxis:
                if t.free:
                    libres.append(f"Taxi-{t.id}")
                else:
                    
                    if t.current_client_id is not None:
                        ocupados.append(f"Taxi-{t.id}(Cliente-{t.current_client_id})")
                    else:
                        ocupados.append(f"Taxi-{t.id}")

            return libres, ocupados
        finally:
            self.sem_taxis.release()

    #asignar taxi
    def assign_taxi(self, client_id: int, ox: float, oy: float) -> Optional[Taxi]:
        """
        - Taxi libre
        - A 2 km del origen 
        - Elegir el mas cercano
        - Empate en distancia: mayor rating medio
        """
        self.sem_taxis.acquire()
        try:
            candidates = []  # lista de candidatos .

            #buscamos taxis libres dentro del radio.
            for t in self.taxis:
                if not t.free:
                    continue

                #distancia del taxi al origen
                d = math.dist((ox, oy), (t.x, t.y))

                #si está dentro del radio, es candidato
                if d <= SEARCH_RADIUS_KM:
                    # Ordenamos por distancia, -rating, id
                    candidates.append((round(d, 6), -t.rating_avg, t.id, t))

            #si no hay taxis disponibles, devolvemos None
            if not candidates:
                return None

            #elegimos el mejor candidato
            candidates.sort()
            chosen = candidates[0][3]

            #marcamos taxi como ocupado y registramos el cliente
            chosen.free = False
            chosen.current_client_id = client_id

            return chosen
        finally:
            self.sem_taxis.release()

    def finish_trip(self, taxi: Taxi, dx: float, dy: float, fare: float, rating: int) -> None:
        """
        Al finalizar un viaje:
        - liberar taxi
        - acumular stats
        - mover taxi a destino (para reparto realista)
        """
        self.sem_taxis.acquire()
        try:
            #liberamos taxi
            taxi.free = True
            taxi.current_client_id = None

            #actualizamos estadísticas
            taxi.services += 1
            taxi.earnings += fare
            taxi.rating_sum += rating
            taxi.rating_count += 1

            #el taxi queda en el destino del viaje
            taxi.x = dx
            taxi.y = dy
        finally:
            self.sem_taxis.release()

    @staticmethod
    def tri_int(a: int, mode: int, b: int) -> int:
        #distribución triangular: más “realista” que uniform
        return int(round(random.triangular(a, b, mode)))

    @staticmethod
    def rand_point() -> Tuple[float, float]:
        #punto aleatorio en el mapa
        return random.uniform(MAP_MIN, MAP_MAX), random.uniform(MAP_MIN, MAP_MAX)

    @staticmethod
    def compute_fare(distance_km: float) -> float:
        # Tarifa base + precio_por_km * distancia.
        eur_km = random.uniform(EUR_PER_KM_MIN, EUR_PER_KM_MAX)
        return round(BASE_FEE_EUR + distance_km * eur_km, 2)


