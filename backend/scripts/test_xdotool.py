"""
Prueba standalone de xdotool. No toca la base de datos ni el bot.
Asume que el operador tiene Telegram Web abierto en Firefox y el cursor
en el cuadro de texto de 'Mensajes guardados' (o cualquier chat de prueba).
"""
import random
import sys
import time

from app.services.xdotool_writer import write_to_active_window


def main() -> int:
    print("Tienes 5 segundos para enfocar Firefox con Telegram Web abierto")
    print("y poner el cursor en el cuadro de texto del chat de prueba.")
    for i in range(5, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    msg = f"prueba xdotool {random.randint(1000, 9999)}"
    print(f"Escribiendo: {msg!r}")

    ok, err = write_to_active_window(msg, press_enter=True)
    if not ok:
        print(f"FALLO: {err}")
        return 1

    print("OK: mensaje escrito y Enter pulsado")
    return 0


if __name__ == "__main__":
    sys.exit(main())