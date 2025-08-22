# apps/core/views.py

from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.decorators import login_required
from .models import Producto, Categoria, Venta, DetalleVenta
from django.utils import timezone
from django.db.models import Sum, F

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
    """
    Vista para listar todos los productos.
    """
    model = Producto
    template_name = 'core/productos_list.html'
    context_object_name = 'productos'
    
    # Restricción para que solo usuarios logueados accedan a la vista
    # Nota: También puedes usar 'LoginRequiredMixin' si prefieres.
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(self.request.get_full_path(), login_url='login')
        return super().dispatch(request, *args, **kwargs)


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