# apps/core/views.py

import csv
import io
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
    
    # Redirección en caso de no estar logueado
    login_url = reverse_lazy('login')

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            # Filtra por nombre, categoría o descripción (insensible a mayúsculas/minúsculas)
            queryset = queryset.filter(
                Q(nombre__icontains=query) |
                Q(descripcion__icontains=query) |
                Q(categoria__nombre__icontains=query)
            ).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Añade el contador de productos al contexto
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
        'precio_venta': str(producto.precio_venta), # Se convierte a string para JSON
        'costo_compra': str(producto.costo_compra) if producto.costo_compra else '0.00',
        'stock': producto.stock,
        'categoria': producto.categoria.nombre if producto.categoria else 'N/A',
        'activo': producto.activo,
        'imagen_url': producto.imagen.url if producto.imagen else '/static/assets/img/placeholder.png'
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
    

class VentaView(View):
    def get(self, request, *args, **kwargs):
        # Aquí podrías cargar datos iniciales si fuera necesario
        productos = Producto.objects.filter(activo=True)
        return render(request, 'core/nueva_venta.html', {'productos': productos})
    

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