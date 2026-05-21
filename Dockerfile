FROM php:8.1-apache

# 1. Instalar extensiones necesarias para SUNAT (SOAP para comunicarse con el webservice)
RUN apt-get update && apt-get install -y \
    libxml2-dev \
    git \
    unzip \
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

# 7. Crear carpeta data y buscar el certificado de prueba dentro de vendor
RUN mkdir -p data && \
    CERT=$(find /var/www/html/vendor -name "cert.pem" -o -name "certificate.pem" | head -1) && \
    if [ -n "$CERT" ]; then cp "$CERT" data/certificate.pem; fi

# 8. Configurar Apache para que apunte a /var/www/html directamente
RUN echo '<Directory /var/www/html>\n\
    AllowOverride All\n\
    Require all granted\n\
</Directory>' > /etc/apache2/conf-available/app.conf \
    && a2enconf app

# 9. Permisos
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80