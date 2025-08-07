from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction

from .forms import ProductoForm
from .models import (
    Producto, StockLocal, Local,
    MovimientoStock, IngresoLote,ImagenProducto, Categoria
)

import os
import uuid
import json
import base64
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from barcode import Code128


# ─────────────────────────────────────────────────────────────────────
# Permisos
# ─────────────────────────────────────────────────────────────────────

def no_es_vendedor(user):
    return not user.groups.filter(name='vendedor').exists()

# ─────────────────────────────────────────────────────────────────────
# PRODUCTO: Crear, listar, buscar, ver detalle
# ─────────────────────────────────────────────────────────────────────
from django.contrib.staticfiles import finders

@login_required
@login_required
@user_passes_test(no_es_vendedor)
def agregar_producto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        precio = request.POST.get('precio_venta', '').strip()
        gramos = request.POST.get('gramos', '0').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        categoria_id = request.POST.get('categoria')
        cantidad = request.POST.get('cantidad', '1').strip()

        errores = []
        if not nombre:
            errores.append("El nombre es obligatorio.")
        if not precio:
            errores.append("El precio es obligatorio.")
        if not categoria_id:
            errores.append("La categoría es obligatoria.")

        try:
            precio = float(precio)
        except ValueError:
            errores.append("El precio debe ser un número válido.")

        try:
            gramos = int(gramos)
        except ValueError:
            gramos = 0

        try:
            cantidad = int(cantidad)
        except ValueError:
            cantidad = 1

        if errores:
            categorias = Categoria.objects.all()
            return render(request, 'agregar_producto.html', {
                'errores': errores,
                'categorias': categorias
            })

        with transaction.atomic():
            producto = Producto(
                nombre=nombre,
                descripcion=descripcion,
                precio_venta=precio,
                gramos=gramos,
                categoria=Categoria.objects.get(id=categoria_id),
                user_made=request.user
            )
            producto.save()

            # Procesar imágenes base64 (cámara)
            webcam_images_data = request.POST.get('webcam_images')
            if webcam_images_data:
                try:
                    webcam_images = json.loads(webcam_images_data)
                    for img_data in webcam_images:
                        format, imgstr = img_data.split(';base64,')
                        ext = format.split('/')[-1]
                        filename = f"{uuid.uuid4()}.{ext}"
                        data = ContentFile(base64.b64decode(imgstr), name=filename)
                        ImagenProducto.objects.create(producto=producto, imagen=data)
                except Exception as e:
                    print(f"Error procesando imágenes: {e}")

            # Crear etiqueta térmica plegable
            codigo = producto.id
            etiqueta_rel_path = generar_etiqueta_plegable(producto.categoria.nombre, codigo, codigo)
            producto.codigo_barras = etiqueta_rel_path
            producto.save()

            # Agregar stock inicial
            local = Local.objects.get(id=1)
            stock_obj, _ = StockLocal.objects.get_or_create(producto=producto, local=local)
            stock_obj.cantidad += cantidad
            stock_obj.save()

            imprimir_etiquetas = request.POST.get('imprimir') == 'true'
            if imprimir_etiquetas and cantidad > 0:
                return render(request, 'imprimir_etiqueta.html', {
                    'etiqueta_url': producto.codigo_barras.url,
                    'cantidad': cantidad,
                    'repeticiones': range(cantidad)
                })

        return redirect('products_app:productos')

    categorias = Categoria.objects.all().order_by('nombre')
    return render(request, 'agregar_producto.html', {'categorias': categorias})

def generar_etiqueta_plegable(nombre_producto, codigo_producto, filename):
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO
    from barcode import Code128
    from barcode.writer import ImageWriter
    import os
    from django.conf import settings
    from django.contrib.staticfiles import finders

    # Convertir código a string con ceros a la izquierda (8 dígitos)
    codigo_str = str(codigo_producto).zfill(6)
    codigo_art = str(codigo_producto)

    # Generar código de barras CODE128 (no EAN8)
    code128 = Code128(codigo_str, writer=ImageWriter())

    # Resolución Zebra ZD220
    dpi = 203
    mm_to_px = lambda mm: int((mm / 25.4) * dpi)

    # Tamaño etiqueta: 66mm x 11mm
    ancho_px = mm_to_px(66)
    alto_px = mm_to_px(11)

    # Tamaño del código de barras dentro de la etiqueta
    ancho_codigo_px = mm_to_px(29)
    alto_codigo_px = mm_to_px(6)
    alto_codigo_px_2 = mm_to_px(5.2)

    # Crear imagen blanca
    etiqueta = Image.new("RGB", (ancho_px, alto_px), "white")
    draw = ImageDraw.Draw(etiqueta)

    # Generar imagen del código
    buffer = BytesIO()
    code128.write(buffer, {
        "module_width": 0.37,
        "module_height": alto_codigo_px,
        "quiet_zone": 1.0,
        "font_size": 0,
        "write_text": False
    })
    buffer.seek(0)
    img_barcode = Image.open(buffer).convert("RGB")
    img_barcode = img_barcode.resize((ancho_codigo_px, alto_codigo_px), Image.LANCZOS)

    # Pegar el código en la etiqueta
    x_barcode = mm_to_px(1)
    y_barcode = mm_to_px(0)
    etiqueta.paste(img_barcode, (x_barcode, y_barcode))

    # Fuente para el número debajo
    font_size = mm_to_px(2.5)
    font_path = finders.find("fonts/DejaVuSans-Bold.ttf")
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()

    # Escribir texto
    text = codigo_str
    text_width, text_height = draw.textsize(text, font=font)
    ajuste_izquierda = mm_to_px(0.8)  # Valor en píxeles para mover el texto hacia la izquierda
    x_text = x_barcode + (ancho_codigo_px - text_width) // 2 - ajuste_izquierda
    y_text = y_barcode + alto_codigo_px_2
    draw.text((x_text, y_text), text, fill="black", font=font)
    
    
    # --- NUEVO: Leyenda "Art. <id>" a la derecha del código ---
    leyenda = f"{nombre_producto}"
    font_size_leyenda = mm_to_px(3.4)

    # Intentar cargar fuente en negrita
    font_bold_path = finders.find("fonts/DejaVuSans-Bold.ttf")
    if font_bold_path:
        font_leyenda = ImageFont.truetype(font_bold_path, font_size_leyenda)
    else:
        font_leyenda = ImageFont.truetype(font_path, font_size_leyenda) if font_path else ImageFont.load_default()

    text_width_leyenda, text_height_leyenda = draw.textsize(leyenda, font=font_leyenda)
    x_leyenda = x_barcode + ancho_codigo_px + mm_to_px(5)  # Espacio entre código y texto
    y_leyenda = y_barcode + (alto_codigo_px - text_height_leyenda) // 2
    draw.text((x_leyenda, y_leyenda), leyenda, fill="black", font=font_leyenda)

    # Guardar etiqueta
    etiquetas_dir = os.path.join(settings.MEDIA_ROOT, 'etiquetas')
    os.makedirs(etiquetas_dir, exist_ok=True)
    ruta_completa = os.path.join(etiquetas_dir, f"{filename}.png")
    etiqueta.save(ruta_completa)

    return f"etiquetas/{filename}.png"


@csrf_exempt
@login_required
def eliminar_producto_api(request, id):
    """
    Elimina lógicamente un producto si no está implicado en una transferencia de stock.
    """
    if request.method == "POST":
        try:
            with transaction.atomic():
                producto = Producto.objects.get(id=id)

                # Verificar si el producto está en alguna transferencia
                implicado_en_transferencia = MovimientoStock.objects.filter(
                    producto=producto
                ).exists()

                if implicado_en_transferencia:
                    return JsonResponse({
                        "success": False,
                        "error": "No se puede eliminar el producto porque está implicado en una transferencia de stock."
                    })

                producto.user_deleted = request.user
                producto.delete()  # Soft delete

                return JsonResponse({"success": True})

        except Producto.DoesNotExist:
            return JsonResponse({"success": False, "error": "Producto no encontrado"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

@login_required
def consultar_precio(request):
    codigo = request.GET.get('codigo')
    if not codigo:
        return JsonResponse({'success': False, 'error': 'Código no proporcionado'})

    try:
        producto = Producto.objects.get(id=codigo)
    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'})

    local_id = request.session.get('local_id')
    local = Local.objects.get(id=local_id) if local_id else None


    # Buscar el stock, si no existe devolver 0
    stock = StockLocal.objects.filter(producto=producto, local=local).first()
    cantidad = stock.cantidad if stock else 0
    fotos = [img.imagen.url for img in producto.imagenes.all()]
    foto_principal = fotos[0] if fotos else ""
    return JsonResponse({
        'success': True,
        'nombre': producto.nombre,
        'precio_venta': str(producto.precio_venta),
        'stock': cantidad,
        'foto':foto_principal
    })


@login_required
@user_passes_test(no_es_vendedor)
def imprimir_etiquetas(request, producto_id):
    cantidad = int(request.GET.get("cantidad", 0))
    producto = get_object_or_404(Producto, id=producto_id)

    if cantidad > 0 and producto.codigo_barras:
        return render(request, 'impresion_etiquetas.html', {
            'etiqueta_url': producto.codigo_barras.url,
            'cantidad': cantidad,
            'repeticiones': range(cantidad),
            'producto_id':producto.id
        })

    return redirect('products_app:detalle_producto', producto_id=producto.id)


@login_required 
def lista_productos(request):
    local_id = request.session.get('local_id')
    local = Local.objects.get(id=local_id) if local_id else None

    # Si el usuario está en el grupo "cargador", filtramos por stock local
    if request.user.groups.filter(name='vendedor').exists():
        productos = Producto.objects.filter(
            stocklocal__local=local,
            stocklocal__cantidad__gt=0
        ).distinct().order_by('-id')
    else:
        # Admin u otros roles no vendedores ni cargadores: todos los productos
        productos = Producto.objects.all().order_by('-id')

    return render(request, 'productos.html', {'productos': productos})

@login_required
def buscar_producto_por_codigo_venta(request):
    codigo = request.GET.get("codigo")
    try:
        producto = Producto.objects.get(id=codigo) 
        # Intentamos obtener el stock
        local_id = request.session.get('local_id')
        local = Local.objects.get(id=local_id) if local_id else None    
        try:
            stock = StockLocal.objects.get(producto=producto, local=local)
            cantidad_stock = stock.cantidad
        except StockLocal.DoesNotExist:
            cantidad_stock = 0
        fotos = [img.imagen.url for img in producto.imagenes.all()]
        foto_principal = fotos[0] if fotos else ""
        data = {
            "nombre": producto.nombre,
            "foto": foto_principal,
            "id": producto.id,
            "stock": cantidad_stock,
            "precio": producto.precio_venta
        }
        return JsonResponse({"success": True, "producto": data})
    except Producto.DoesNotExist:
        return JsonResponse({"success": False, "error": "Producto no encontrado"})
 
@login_required

def buscar_producto_por_codigo(request):
    codigo = request.GET.get("codigo")
    local_id= request.GET.get("local_id")
    try:
        producto = Producto.objects.get(id=codigo)

        # Si local_id es "0" o "" asumimos que es Central (puedes adaptar la lógica)
        if not local_id or local_id in ["0", ""]:
            local = Local.objects.get(nombre="Central")  # O usa tu lógica para obtener Central
        else:
            local = Local.objects.get(id=local_id)

        # Intentamos obtener el stock
        try:
            stock = StockLocal.objects.get(producto=producto, local=local)
            cantidad_stock = stock.cantidad
        except StockLocal.DoesNotExist:
            cantidad_stock = 0
        fotos = [img.imagen.url for img in producto.imagenes.all()]
        foto_principal = fotos[0] if fotos else ""
        data = {
            "nombre": producto.nombre,
            "foto": foto_principal,
            "id": producto.id,
            "stock": cantidad_stock,
            "precio": producto.precio_venta
        }
        return JsonResponse({"success": True, "producto": data})
    except Producto.DoesNotExist:
        return JsonResponse({"success": False, "error": "Producto no encontrado"})
 
from applications.ventas.models import DetalleVenta  # Asegurate de importar el modelo


@login_required
def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    es_admin = request.user.is_superuser or request.user.groups.filter(name="administrador").exists()
    
    if es_admin:
        stock_por_local = StockLocal.objects.filter(producto=producto).select_related('local')
    else:
        local_id = request.session.get('local_id')
        local = Local.objects.get(id=local_id) if local_id else None
        stock_por_local = StockLocal.objects.filter(producto=producto, local=local)

    total_stock = sum(s.cantidad for s in stock_por_local)

    # Obtener ventas relacionadas a este producto
    ventas = DetalleVenta.objects.filter(producto=producto).select_related('venta__local', 'venta__user_made').order_by('-venta__fecha')

    return render(request, 'detalle_producto.html', {
        'producto': producto,
        'stock_por_local': stock_por_local,
        'total_stock': total_stock,
        'ventas': ventas,  # nuevo contexto para el modal
    })

@login_required
def imprimir_codigo(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'imprimir_codigo.html', {'producto': producto})


# ─────────────────────────────────────────────────────────────────────
# INGRESO DE MERCADERÍA
# ─────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(no_es_vendedor)
def ingreso_mercaderia(request):
    local_id = request.GET.get("local_id") or 1
    fecha_actual = timezone.now().strftime("%d/%m/%Y")
    locales = Local.objects.exclude(nombre="Central")
    return render(request, 'ingreso_mercaderia.html', {
        'fecha_actual': fecha_actual,
        'local_id': local_id,
        'locales':locales
    })


@login_required
@csrf_exempt
@user_passes_test(no_es_vendedor)  # Asegúrate de que esta func existe
def registrar_ingreso(request):
    """Registrar una transferencia de productos entre Central y un Local involucrado."""
    if request.method != 'POST':
        return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)
        productos = data.get("productos", [])
        local_id = data.get("local_id")
        tipo = data.get("tipo")

        if not local_id or not tipo:
            return JsonResponse({"success": False, "error": "Faltan datos requeridos (local_id, tipo)."}, status=400)

        # Verificación de existencia de locales
        try:
            local_involucrado = Local.objects.get(id=local_id)
            central = Local.objects.get(nombre="Central")
        except Local.DoesNotExist:
            return JsonResponse({"success": False, "error": "Local no encontrado."}, status=404)

        # Crear el lote de ingreso
        with transaction.atomic():
            lote = IngresoLote.objects.create(local=local_involucrado, tipo=tipo, fecha=timezone.now(), user_made=request.user)

            for item in productos:
                producto_id = item.get("id")
                cantidad = int(item.get("cantidad", 0))
                if cantidad <= 0:
                    return JsonResponse({"success": False, "error": f"Cantidad no válida para producto ID {producto_id}."}, status=400)

                producto = Producto.objects.filter(id=producto_id).first()
                if not producto:
                    return JsonResponse({"success": False, "error": f"Producto ID {producto_id} no encontrado."}, status=404)

                # Definir local de origen y destino según el tipo de operación
                if tipo == "entrada":
                    origen = central
                    destino = local_involucrado
                else:
                    origen = local_involucrado
                    destino = central

                # Verificación de stock en el local de origen
                stock_origen, _ = StockLocal.objects.get_or_create(producto=producto, local=origen, defaults={'cantidad': 0})
                if stock_origen.cantidad < cantidad:
                    return JsonResponse({"success": False, "error": f"No hay suficiente stock de {producto.nombre} en el local {origen.nombre}. Stock actual: {stock_origen.cantidad}"}, status=400)

                # Crear movimiento de stock
                MovimientoStock.objects.create(
                    producto=producto,
                    cantidad=cantidad,
                    lote=lote,
                    user_made=request.user
                )
                # Actualizar stock origen
                stock_origen.cantidad -= cantidad
                stock_origen.save()

                # Actualizar stock destino
                stock_destino, _ = StockLocal.objects.get_or_create(producto=producto, local=destino, defaults={'cantidad': 0})
                stock_destino.cantidad += cantidad
                stock_destino.save()

        return JsonResponse({"success": True}, status=200)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
# CONSULTAS DE INGRESOS
# ─────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(no_es_vendedor)
def lista_ingresos(request):
    ingresos = IngresoLote.objects.all().order_by('-fecha')
    return render(request, 'ingresos.html', {'ingresos': ingresos})


@login_required
@user_passes_test(no_es_vendedor)
def detalle_ingreso(request, ingreso_id):
    ingreso = get_object_or_404(IngresoLote, id=ingreso_id)
    productos = ingreso.movimientos.all()

    return render(request, 'detalle_ingreso.html', {
        'ingreso': ingreso,
        'productos': productos,
    })


from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import IngresoLote
from datetime import timedelta
from django.utils import timezone

@login_required
@user_passes_test(no_es_vendedor)
def eliminar_ingreso(request, ingreso_id):
    """Elimina un IngresoLote y revierte los cambios de stock, si no pasaron 30 minutos."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido."}, status=405)

    lote = get_object_or_404(IngresoLote, id=ingreso_id)

    # ✅ Verificar si pasaron más de 30 minutos
    tiempo_limite = lote.fecha + timedelta(minutes=30)
    if timezone.now() > tiempo_limite:
        return JsonResponse({
            "success": False,
            "error": "Eliminacion restringida debido a que paso mas de 30 minutos de su creacion ."
        }, status=403)

    try:
        central = Local.objects.get(nombre="Central")
    except Local.DoesNotExist:
        return JsonResponse({"success": False, "error": "Local 'Central' no encontrado."}, status=404)

    try:
        with transaction.atomic():
            movimientos = MovimientoStock.objects.filter(lote=lote)

            for movimiento in movimientos:
                producto = movimiento.producto
                cantidad = movimiento.cantidad
                local_involucrado = lote.local

                if lote.tipo == "entrada":
                    stock_local_involucrado = StockLocal.objects.get(producto=producto, local=local_involucrado)
                    stock_central = StockLocal.objects.get(producto=producto, local=central)

                    if stock_local_involucrado.cantidad < cantidad:
                        raise ValueError(f"No hay suficiente stock en {local_involucrado.nombre} para revertir producto {producto.nombre}")

                    stock_local_involucrado.cantidad -= cantidad
                    stock_local_involucrado.save()

                    stock_central.cantidad += cantidad
                    stock_central.save()

                else:
                    stock_central = StockLocal.objects.get(producto=producto, local=central)
                    stock_local_involucrado = StockLocal.objects.get(producto=producto, local=local_involucrado)

                    if stock_central.cantidad < cantidad:
                        raise ValueError(f"No hay suficiente stock en Central para revertir producto {producto.nombre}")

                    stock_central.cantidad -= cantidad
                    stock_central.save()

                    stock_local_involucrado.cantidad += cantidad
                    stock_local_involucrado.save()

            movimientos.delete()
            lote.delete()

            return JsonResponse({"success": True, "message": f"Ingreso {lote.id} eliminado y stock revertido correctamente."})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"No se pudo eliminar el ingreso. Error: {str(e)}"}, status=500)
