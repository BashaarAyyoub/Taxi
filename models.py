
#modelos de datos básicos usando dataclass para claridad
from dataclasses import dataclass  #para definir estructuras de datos de forma limpia
from typing import Optional        #para tipos opcionales 


@dataclass
class Taxi:
    #identificador del taxi
    id: int

    #posición actual del taxi en el mapa (x,y)
    x: float
    y: float

    #estado del taxi
    free: bool = True

    #cliente actual asignado 
    current_client_id: Optional[int] = None

    #estadísticas acumuladas del día
    services: int = 0         #número de servicios realizados
    earnings: float = 0.0     #Ganancias acumuladas del día
    rating_sum: float = 0.0   #Suma total de ratings recibidos
    rating_count: int = 0     #número de ratings recibidos

    @property
    def rating_avg(self) -> float:
        #rating medio
        return (self.rating_sum / self.rating_count) if self.rating_count else 0.0


