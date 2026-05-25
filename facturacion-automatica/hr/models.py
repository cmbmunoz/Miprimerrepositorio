from dataclasses import dataclass, field
from datetime import date


@dataclass
class Proyecto:
    id: str
    nombre: str
    cliente_nombre: str
    cliente_cuit: str
    cliente_email: str
    descripcion: str = ""
    activo: bool = True


@dataclass
class Persona:
    id: str
    nombre: str
    proyecto_id: str
    fecha_ingreso: date
    tarifa_mensual: float
    moneda: str = "ARS"
    activo: bool = True
    observaciones: str = ""
