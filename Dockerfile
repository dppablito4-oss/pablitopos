FROM php:8.1-apache

# 1. Instalar extensiones necesarias para SUNAT
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    git \
    unzip \
    openssl \
    && docker-php-ext-install soap \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Habilitar mod_rewrite de Apache
RUN a2enmod rewrite

# 3. Instalar Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# 4. Copiar composer.json primero (para cachear dependencias en Docker)
COPY composer.json .

# 5. Instalar dependencias de Greenter
RUN composer install --no-dev --optimize-autoloader --no-interaction

# 6. Copiar el index.php (la API)
COPY index.php .

# 7. Crear carpeta data y generar certificado de PRUEBA para SUNAT Beta
#    En producción, reemplaza data/certificate.pem con tu certificado real
RUN mkdir -p data && \
    openssl req -x509 -nodes -days 3650 \
    -newkey rsa:2048 \
    -keyout data/key.pem \
    -out data/cert_only.pem \
    -subj "/C=PE/ST=Lima/L=Lima/O=GRAFIPLOT VASQUEZ/CN=pablitopos" && \
    cat data/key.pem data/cert_only.pem > data/certificate.pem && \
    rm data/key.pem data/cert_only.pem

# 8. Configurar Apache
RUN echo '<Directory /var/www/html>\n\
    AllowOverride All\n\
    Require all granted\n\
</Directory>' > /etc/apache2/conf-available/app.conf \
    && a2enconf app

# 9. Permisos
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80