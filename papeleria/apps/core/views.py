# apps/core/views.py

import csv
import io
import json
from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.decorators import login_required
from .models import Producto, Categoria, Venta, DetalleVenta
from django.utils import timezone
from django.db.models import Sum, F
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from datetime import timedelta
from .utils import enviar_notificacion_stock_cero
# ======================================================================
# VISTAS DEL DASHBOARD Y AUTENTICACIÓN
# ======================================================================

@login_required
def dashboard(request):
    today = timezone.now().date()
    ventas_hoy = Venta.objects.filter(fecha_venta__date=today).aggregate(total_ventas=Sum('total'))
    total_ventas_hoy = ventas_hoy['total_ventas'] if ventas_hoy['total_ventas'] else 0
    
    productos_bajo_stock = Producto.objects.filter(stock__lte=5).order_by('stock')[:5] # Muestra los 5 primeros

    productos_mas_vendidos = DetalleVenta.objects.filter(
        venta__fecha_venta__date__gte=today - timezone.timedelta(days=30)
    ).values('producto__nombre').annotate(
        cantidad_total=Sum('cantidad')
    ).order_by('-cantidad_total')[:5]
    
    context = {
        'total_ventas_hoy': total_ventas_hoy,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_mas_vendidos': productos_mas_vendidos,
    }
    
    return render(request, 'core/dashboard.html', context)

# ======================================================================
# VISTAS DE PRODUCTOS
# ======================================================================

class ProductoListView(ListView):
    model = Producto
    template_name = 'core/productos_list.html'
    context_object_name = 'productos'
    login_url = reverse_lazy('login')

    def get_queryset(self):
        # Esta vista ahora solo obtiene todos los productos
        # La lógica de filtrado se maneja en el frontend con JS
        return super().get_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Aquí pasamos el conteo total de productos
        context['total_productos'] = self.get_queryset().count()
        return context

class ProductoUpdateView(UpdateView):
    model = Producto
    fields = ['nombre', 'descripcion', 'codigo_barras', 'precio_venta', 'costo_compra', 'stock', 'categoria', 'activo']
    template_name = 'core/producto_up_form.html'
    success_url = reverse_lazy('core:producto-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all()
        return context
    


def producto_detail_json(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    data = {
        'nombre': producto.nombre,
        'descripcion': producto.descripcion,
        'codigo_barras': producto.codigo_barras,
        'precio_venta': str(producto.precio_venta),
        'costo_compra': str(producto.costo_compra),
        'stock': producto.stock,
        'categoria': producto.categoria.nombre if producto.categoria else "",
        'imagen': producto.imagen.url if producto.imagen else "",
    }
    return JsonResponse(data)

class ProductoCreateView(CreateView):
    """
    Vista para crear un nuevo producto.
    """
    model = Producto
    template_name = 'core/producto_form.html'
    fields = ['nombre', 'descripcion', 'codigo_barras', 'precio_venta', 'costo_compra', 'stock', 'categoria']
    success_url = reverse_lazy('core:producto-list')
    
    # Restricción para que solo usuarios logueados accedan a la vista
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(self.request.get_full_path(), login_url='login')
        return super().dispatch(request, *args, **kwargs)


# ======================================================================
# VISTAS DE CATEGORÍAS
# ======================================================================

class CategoriaListView(ListView):
    """
    Vista para listar todas las categorías.
    """
    model = Categoria
    template_name = 'core/categoria_list.html'
    context_object_name = 'categorias'

    # Restricción para que solo usuarios logueados accedan a la vista
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(self.request.get_full_path(), login_url='login')
        return super().dispatch(request, *args, **kwargs)


class CategoriaCreateView(CreateView):
    """
    Vista para crear una nueva categoría.
    """
    model = Categoria
    template_name = 'core/categoria_form.html'
    fields = ['nombre', 'descripcion']
    success_url = reverse_lazy('core:categoria-list')

    # Restricción para que solo usuarios logueados accedan a la vista
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(self.request.get_full_path(), login_url='login')
        return super().dispatch(request, *args, **kwargs)

class CategoriaDeleteView(DeleteView):
    model = Categoria
    template_name = 'core/categoria_confirm_delete.html'
    success_url = reverse_lazy('core:categoria-list')
    login_url = reverse_lazy('login')

class VentaView(View):
    def get(self, request, *args, **kwargs):
        productos = Producto.objects.filter(activo=True)
        return render(request, 'core/nueva_venta.html', {'productos': productos})

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            data = json.loads(request.body)
            cart_items = data.get('cart', {})
            
            if not cart_items:
                return JsonResponse({'success': False, 'message': 'El carrito está vacío.'}, status=400)

            total_venta = 0
            
            venta = Venta.objects.create(total=0)

            for item_id, item_data in cart_items.items():
                producto = Producto.objects.get(pk=item_id)
                cantidad_vendida = item_data['cantidad']
                
                if producto.stock < cantidad_vendida:
                    transaction.set_rollback(True)
                    return JsonResponse({'success': False, 'message': f'Stock insuficiente para {producto.nombre}.'}, status=400)
                
                # Actualizar el stock
                producto.stock -= cantidad_vendida
                producto.save()
                if producto.stock == 0:
                    enviar_notificacion_stock_cero(producto.nombre)
                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad_vendida,
                    precio_unitario=producto.precio_venta
                )
                
                total_venta += producto.precio_venta * cantidad_vendida

            venta.total = total_venta
            venta.save()
            
            return JsonResponse({'success': True, 'message': f'Venta procesada con éxito. Total: ${total_venta:.2f}'}, status=200)

class VentaDeleteView(DeleteView):
    model = Venta
    template_name = 'core/venta_confirm_delete.html'
    success_url = reverse_lazy('core:ventas-list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        with transaction.atomic():
            detalles = DetalleVenta.objects.filter(venta=self.object)
            for detalle in detalles:
                producto = detalle.producto
                producto.stock += detalle.cantidad
                producto.save()
            
            self.object.delete()
        
        return JsonResponse({'success': True, 'message': 'Venta eliminada correctamente y stock devuelto.'})
    

class VentasListView(ListView):
    model = Venta
    template_name = 'core/ventas_list.html'
    context_object_name = 'ventas'
    ordering = ['-fecha_venta']

class UploadCSVView(View):
    template_name = 'core/upload_csv.html'

    def get(self, request, *args, **kwargs):
        """Muestra el formulario de subida."""
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        """Procesa el archivo CSV subido."""
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            
            # Decodificar el archivo en memoria
            csv_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            
            try:
                # Obtenemos o creamos las categorías
                papeleria_cat, _ = Categoria.objects.get_or_create(nombre='Papelería')
                dulces_cat, _ = Categoria.objects.get_or_create(nombre='Dulces')
                
                for row in csv_reader:
                    # Lógica para determinar la categoría
                    categoria_producto = papeleria_cat
                    
                    Producto.objects.update_or_create(
                        nombre=row['Producto'],
                        defaults={
                            'stock': int(row['Cantidad']),
                            'costo_compra': float(row['Precio Unitario (Costo)'].replace('$', '').replace(',', '')),
                            'precio_venta': float(row['Precio de Venta Unitario (30% Margen)'].replace('$', '').replace(',', '')),
                            'categoria': categoria_producto,
                        }
                    )
                messages.success(request, '¡Productos cargados exitosamente!')
            except KeyError as e:
                messages.error(request, f'Error en el formato del CSV. Falta la columna: {e}.')
            except Exception as e:
                messages.error(request, f'currió un error inesperado: {e}.')
        else:
            messages.error(request, 'No se encontró el archivo en la solicitud.')
        
        return redirect('core:upload_csv')
    

class ReportesVentaView(View):
    def get(self, request, *args, **kwargs):
        # Valores iniciales para el reporte (últimos 30 días)
        fecha_fin = timezone.now().date()
        fecha_inicio = fecha_fin - timedelta(days=30)

        # Si el usuario envía un rango de fechas, lo usamos
        if request.GET.get('fecha_inicio') and request.GET.get('fecha_fin'):
            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')

        # Filtrar las ventas por el rango de fechas
        ventas = Venta.objects.filter(fecha_venta__date__range=[fecha_inicio, fecha_fin])
        
        # Calcular el total de ventas
        total_ventas = ventas.aggregate(total=Sum('total'))['total'] or 0

        # Calcular el total de productos vendidos
        total_productos_vendidos = DetalleVenta.objects.filter(
            venta__in=ventas
        ).aggregate(total_cantidad=Sum('cantidad'))['total_cantidad'] or 0

        contexto = {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'ventas': ventas,
            'total_ventas': total_ventas,
            'total_transacciones': ventas.count(),
            'total_productos_vendidos': total_productos_vendidos,
        }
        
        return render(request, 'core/reportes_ventas.html', contexto)