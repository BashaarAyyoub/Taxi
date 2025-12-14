# config.py

# Simulación de tiempo
SIM_MINUTE_SECONDS = 0.04          # 1 minuto simulado = 0.04s reales
DAY_MINUTES = 24 * 60              # 00:00 -> 24:00

# Mapa (más denso para que el radio 2 km funcione y haya flujo)
MAP_MIN = 0.0
MAP_MAX = 10.0

# Asignación
SEARCH_RADIUS_KM = 2.0

# Duración de los viajes (minutos) - razonable
TRIP_MIN = 12
TRIP_MODE = 20
TRIP_MAX = 45

# Espera entre viajes por cliente (minutos) - aleatoria razonable
WAIT_MIN = 10
WAIT_MODE = 30
WAIT_MAX = 90

# Reintento si no encuentra taxi (minutos)
RETRY_MIN = 2
RETRY_MODE = 5
RETRY_MAX = 12

# Tarifa simple
BASE_FEE_EUR = 2.50
EUR_PER_KM_MIN = 1.8
EUR_PER_KM_MAX = 3.2


