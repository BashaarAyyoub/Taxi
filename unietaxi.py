import threading
import time
import random
import math

# =========================
# CONFIG (ajustable)
# =========================
SIM_MINUTE_SECONDS = 0.04          # 1 minuto simulado = 0.04s reales
DAY_MINUTES = 24 * 60             # 00:00 -> 24:00

# Mapa (más denso para que radio 2 km funcione y haya flujo)
MAP_MIN = 0.0
MAP_MAX = 10.0                    # antes 20 daba pocos matches con radio 2

SEARCH_RADIUS_KM = 2.0

# Duración del viaje (min) - razonable
TRIP_MIN = 12
TRIP_MODE = 20
TRIP_MAX = 45

# Espera entre viajes por cliente (min) - aleatoria razonable
WAIT_MIN = 10
WAIT_MODE = 30
WAIT_MAX = 90

# Reintento si no encuentra taxi (min)
RETRY_MIN = 2
RETRY_MODE = 5
RETRY_MAX = 12

# Tarifa simple
BASE_FEE_EUR = 2.50
EUR_PER_KM_MIN = 1.8
EUR_PER_KM_MAX = 3.2

# =========================
# SEMÁFOROS BINARIOS (PDF)
# =========================
sem_taxis = threading.Semaphore(1)
sem_clock = threading.Semaphore(1)
sem_services = threading.Semaphore(1)
sem_print = threading.Semaphore(1)

# =========================
# ESTADO GLOBAL
# =========================
current_minute = 0
day_finished = False
services_active = 0


# =========================
# UTILIDADES
# =========================
def sleep_minutes(m: int) -> None:
    time.sleep(m * SIM_MINUTE_SECONDS)


def minute_to_clock(m: int) -> str:
    # si se pasa de 24:00, lo mostramos como (+1d)
    day_offset = m // DAY_MINUTES
    mm = m % DAY_MINUTES
    hh = mm // 60
    mi = mm % 60
    if day_offset <= 0:
        return f"{hh:02d}:{mi:02d}"
    return f"{hh:02d}:{mi:02d} (+{day_offset}d)"


def tri_int(a: int, mode: int, b: int) -> int:
    return int(round(random.triangular(a, b, mode)))


def show_taxi_status(taxis) -> None:
    libres = []
    ocupados = []
    # ya estamos en sem_print cuando se llama, pero el estado está protegido por sem_taxis
    sem_taxis.acquire()
    try:
        for t in taxis:
            if t["free"]:
                libres.append(f"Taxi-{t['id']}")
            else:
                if t["current_client"] is None:
                    ocupados.append(f"Taxi-{t['id']}")
                else:
                    ocupados.append(f"Taxi-{t['id']}(Cliente-{t['current_client']})")
    finally:
        sem_taxis.release()

    print("Taxis libres:", ", ".join(libres) if libres else "Ninguno")
    print("Taxis ocupados:", ", ".join(ocupados) if ocupados else "Ninguno")
    print("-" * 70)


def read_positive_int(prompt: str) -> int:
    while True:
        try:
            v = int(input(prompt).strip())
            if v > 0:
                return v
        except ValueError:
            pass
        print("Introduce un entero positivo.")


# =========================
# RELOJ 00:00 -> 24:00
# =========================
def clock_thread():
    global current_minute, day_finished
    while True:
        sleep_minutes(1)
        sem_clock.acquire()
        try:
            if current_minute >= DAY_MINUTES:
                day_finished = True
                break
            current_minute += 1
        finally:
            sem_clock.release()


def now_minute() -> int:
    sem_clock.acquire()
    try:
        return current_minute
    finally:
        sem_clock.release()


def is_day_finished() -> bool:
    sem_clock.acquire()
    try:
        return day_finished
    finally:
        sem_clock.release()


# =========================
# ASIGNACIÓN TAXI
# =========================
def assign_taxi(taxis, client_id: int, ox: float, oy: float):
    """
    Radio 2km, más cercano. Empate -> mejor rating medio.
    """
    sem_taxis.acquire()
    try:
        candidates = []
        for t in taxis:
            if not t["free"]:
                continue
            d = math.dist((ox, oy), (t["x"], t["y"]))
            if d <= SEARCH_RADIUS_KM:
                rating_avg = (t["rating_sum"] / t["rating_count"]) if t["rating_count"] else 0.0
                candidates.append((round(d, 6), -rating_avg, t["id"], t))

        if not candidates:
            return None

        candidates.sort()
        chosen = candidates[0][3]
        chosen["free"] = False
        chosen["current_client"] = client_id
        return chosen
    finally:
        sem_taxis.release()


def compute_fare(distance_km: float) -> float:
    eur_km = random.uniform(EUR_PER_KM_MIN, EUR_PER_KM_MAX)
    return round(BASE_FEE_EUR + distance_km * eur_km, 2)


# =========================
# CLIENTE (THREAD)
# =========================
class Client(threading.Thread):
    def __init__(self, client_id: int, taxis):
        super().__init__(daemon=True)
        self.client_id = client_id
        self.taxis = taxis

    def run(self):
        global services_active

        # desfase inicial para que no arranquen todos iguales
        sleep_minutes(random.randint(0, 10))

        while True:
            # NO iniciar viajes después de 24:00
            if is_day_finished() or now_minute() >= DAY_MINUTES:
                break

            # Origen y destino (uniformes en el mapa para que “fluya” en todo el día)
            ox = random.uniform(MAP_MIN, MAP_MAX)
            oy = random.uniform(MAP_MIN, MAP_MAX)
            dx = random.uniform(MAP_MIN, MAP_MAX)
            dy = random.uniform(MAP_MIN, MAP_MAX)
            distance = math.dist((ox, oy), (dx, dy))

            taxi = assign_taxi(self.taxis, self.client_id, ox, oy)
            if taxi is None:
                # reintento razonable
                retry = max(1, tri_int(RETRY_MIN, RETRY_MODE, RETRY_MAX))
                sleep_minutes(retry)
                continue

            start = now_minute()
            duration = max(1, tri_int(TRIP_MIN, TRIP_MODE, TRIP_MAX))
            end = start + duration  # puede pasar de 24:00, y SE HACE IGUAL

            sem_services.acquire()
            services_active += 1
            sem_services.release()

            # Print inicio + estado taxis
            sem_print.acquire()
            try:
                print(f"\nTaxi-{taxi['id']} inicia servicio con Cliente-{self.client_id}")
                print(f"Hora inicio: {minute_to_clock(start)}")
                print(f"Hora fin prevista: {minute_to_clock(end)}")
                print(f"Origen: ({ox:.2f}, {oy:.2f}) → Destino: ({dx:.2f}, {dy:.2f})")
                print(f"Distancia: {distance:.2f} km | Duración: {duration} min")
                show_taxi_status(self.taxis)
            finally:
                sem_print.release()

            # Simular viaje
            sleep_minutes(duration)

            rating = random.randint(1, 5)
            fare = compute_fare(distance)

            # Actualizar taxi (incluye moverlo al destino para repartir servicios)
            sem_taxis.acquire()
            try:
                taxi["free"] = True
                taxi["current_client"] = None
                taxi["services"] += 1
                taxi["earnings"] += fare
                taxi["rating_sum"] += rating
                taxi["rating_count"] += 1
                taxi["x"] = dx
                taxi["y"] = dy
            finally:
                sem_taxis.release()

            sem_services.acquire()
            services_active -= 1
            sem_services.release()

            # Print fin + estado taxis
            sem_print.acquire()
            try:
                print(f"Servicio finalizado | Cliente-{self.client_id} → Taxi-{taxi['id']}")
                print(f"Hora fin real: {minute_to_clock(end)}")
                print(f"Coste: {fare:.2f} € | Rating: {rating}")
                show_taxi_status(self.taxis)
            finally:
                sem_print.release()

            # Espera razonable antes de otro viaje
            wait = max(1, tri_int(WAIT_MIN, WAIT_MODE, WAIT_MAX))
            sleep_minutes(wait)


# =========================
# RESUMEN FINAL
# =========================
def final_summary(taxis):
    print("\n" + "=" * 50)
    print("RESUMEN FINAL DEL DÍA")
    print("=" * 50)

    # snapshot seguro
    sem_taxis.acquire()
    try:
        snapshot = [dict(t) for t in taxis]
    finally:
        sem_taxis.release()

    top_g = None
    top_r = None

    for t in snapshot:
        rating_avg = (t["rating_sum"] / t["rating_count"]) if t["rating_count"] else 0.0
        print(
            f"Taxi-{t['id']} | Servicios: {t['services']} | "
            f"Ganancias: {t['earnings']:.2f} € | Rating medio: {rating_avg:.2f}"
        )

        if top_g is None or t["earnings"] > top_g["earnings"]:
            top_g = t
        if top_r is None or rating_avg > ((top_r["rating_sum"] / top_r["rating_count"]) if top_r["rating_count"] else 0.0):
            top_r = t

    if top_g:
        print(f"\n🏆 Taxi con más ganancias: Taxi-{top_g['id']}")
    if top_r:
        best_rating = (top_r["rating_sum"] / top_r["rating_count"]) if top_r["rating_count"] else 0.0
        print(f"⭐ Taxi mejor valorado: Taxi-{top_r['id']} ({best_rating:.2f})")


# =========================
# MAIN
# =========================
def main():
    global services_active

    n_taxis = read_positive_int("Ingrese número de taxis: ")
    n_clients = read_positive_int("Ingrese número de clientes: ")

    taxis = []
    for i in range(1, n_taxis + 1):
        taxis.append({
            "id": i,
            "x": random.uniform(MAP_MIN, MAP_MAX),
            "y": random.uniform(MAP_MIN, MAP_MAX),
            "free": True,
            "current_client": None,
            "services": 0,
            "earnings": 0.0,
            "rating_sum": 0.0,
            "rating_count": 0,
        })

    # Reloj
    ct = threading.Thread(target=clock_thread)
    ct.start()

    # Clientes
    clients = [Client(i, taxis) for i in range(1, n_clients + 1)]
    for c in clients:
        c.start()

    # Esperar: fin del día + que terminen los servicios en curso
    while True:
        finished = is_day_finished()
        sem_services.acquire()
        active = services_active
        sem_services.release()

        if finished and active == 0:
            break
        time.sleep(0.1)

    final_summary(taxis)


if __name__ == "__main__":
    main()
