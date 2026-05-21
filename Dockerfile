FROM php:8.1-apache

# 1. Instalamos las librerías del sistema necesarias para las firmas XML de SUNAT
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    git \
    unzip \
    && docker-php-ext-install soap

# 2. Habilitamos mod_rewrite de Apache (vital para que funcionen las URLs de la API)
RUN a2enmod rewrite

# 3. Instalamos Composer de forma automática
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# 4. Descargamos el código fuente oficial de Lycet (API de Greenter) directamente aquí
RUN git clone https://github.com/giansalex/lycet.git .

# 5. Instalamos las dependencias de Lycet
RUN composer install --no-dev --optimize-autoloader

# 6. Damos permisos al servidor web para crear los archivos PDF/XML
RUN chown -R www-data:www-data /var/www/html
RUN chmod -R 775 /var/www/html

EXPOSE 80