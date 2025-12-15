#Aquí guardamos todos los parámetros para ajustar la simulación sin tocar la lógica

#Velocidad: 1 minuto simulado = SIM_MINUTE_SECONDS segundos reales.
SIM_MINUTE_SECONDS = 0.04

#Jornada completa: de 00:00 a 24:00 = 1440 minutos simulados.
DAY_MINUTES = 24 * 60

#Mapa de la ciudad 
MAP_MIN = 0.0
MAP_MAX = 10.0

#Radio máximo de búsqueda: 2 km.
SEARCH_RADIUS_KM = 2.0

#Duración del viaje (minutos) usando distribución triangular.
TRIP_MIN = 12
TRIP_MODE = 20
TRIP_MAX = 45

#Espera entre viajes de un mismo cliente triangular.
WAIT_MIN = 10
WAIT_MODE = 30
WAIT_MAX = 90

#Si un cliente no encuentra taxi, reintenta más tarde.
RETRY_MIN = 2
RETRY_MODE = 5
RETRY_MAX = 12

# Tarifa simple: base + (euros_por_km * distancia).
BASE_FEE_EUR = 2.50
EUR_PER_KM_MIN = 1.8
EUR_PER_KM_MAX = 3.2



