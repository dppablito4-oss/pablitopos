<?php
// ===================================================
// API DE FACTURACIÓN ELECTRÓNICA - PABLITO POS
// ===================================================
// Recibe los datos del carrito desde React (POS.jsx)
// Firma el XML, lo envía a SUNAT y devuelve el hash
// para el QR del ticket.

header("Content-Type: application/json; charset=utf-8");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");

// Responder rápido a preflight CORS
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require __DIR__ . '/vendor/autoload.php';

use Greenter\Model\Client\Client;
use Greenter\Model\Company\Company;
use Greenter\Model\Company\Address;
use Greenter\Model\Sale\Invoice;
use Greenter\Model\Sale\SaleDetail;
use Greenter\Model\Sale\Legend;
use Greenter\See;
use Greenter\Ws\Services\SunatEndpoints;

// =============================================
// ENDPOINT DE HEALTH CHECK (GET /)
// =============================================
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    echo json_encode([
        "status" => "ok",
        "service" => "Pablito POS - API Facturación",
        "version" => "1.1.0",
        "timestamp" => date('c')
    ]);
    exit();
}

// =============================================
// ENDPOINT PRINCIPAL: EMITIR BOLETA (POST /)
// =============================================
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(["success" => false, "error" => "Método no permitido. Usa POST."]);
    exit();
}

// 1. Leer datos que envía React (JSON del body)
$input = json_decode(file_get_contents('php://input'), true);

if (!$input) {
    http_response_code(400);
    echo json_encode(["success" => false, "error" => "No se recibieron datos. Envía un JSON válido."]);
    exit();
}

// 2. Extraer datos del request
$ruc        = $input['ruc'] ?? '20000000001';
$razon      = $input['razonSocial'] ?? 'EMPRESA DE PRUEBA';
$direccion  = $input['direccion'] ?? 'AV PRINCIPAL S/N';
$serie      = $input['serie'] ?? 'B001';
$correlativo = $input['correlativo'] ?? '1';
$clienteDoc = $input['clienteDoc'] ?? '00000000';
$clienteNom = $input['clienteNombre'] ?? 'CLIENTE VARIOS';
$clienteTipo = $input['clienteTipoDoc'] ?? '1'; // 1=DNI, 6=RUC
$items      = $input['items'] ?? [];
$subtotal   = floatval($input['subtotal'] ?? 0);
$igv        = floatval($input['igv'] ?? 0);
$total      = floatval($input['total'] ?? 0);
$leyenda    = $input['leyenda'] ?? 'SON CERO CON 00/100 SOLES';

// Validar que haya items
if (empty($items)) {
    http_response_code(400);
    echo json_encode(["success" => false, "error" => "La boleta debe tener al menos un producto."]);
    exit();
}

// 3. Configurar conexión con SUNAT
$see = new See();
$see->setService(SunatEndpoints::FE_BETA);
$see->setClaveSOL($ruc, 'MODDATOS', 'MODDATOS');

// Certificado digital
$certPath = getenv('CERT_PATH') ?: __DIR__ . '/data/certificate.pem';
if (!file_exists($certPath)) {
    $certPath = glob(__DIR__ . '/vendor/greenter/*/src/*/Resources/cert.pem')[0] ?? '';
}
if (!file_exists($certPath)) {
    http_response_code(500);
    echo json_encode(["success" => false, "error" => "No se encontró el certificado digital."]);
    exit();
}
$see->setCertificate(file_get_contents($certPath));

// 4. Datos de la empresa emisora
$address = new Address();
$address->setUbigueo('150101')
    ->setDepartamento('LIMA')
    ->setProvincia('LIMA')
    ->setDistrito('LIMA')
    ->setUrbanizacion('-')
    ->setDireccion($direccion)
    ->setCodLocal('0000');

$company = new Company();
$company->setRuc($ruc)
    ->setRazonSocial($razon)
    ->setNombreComercial($razon)
    ->setAddress($address);

// 5. Datos del cliente
$client = new Client();
$client->setTipoDoc($clienteTipo)
    ->setNumDoc($clienteDoc)
    ->setRznSocial($clienteNom);

// 6. Crear la boleta electrónica
$invoice = new Invoice();
$invoice->setUblVersion('2.1')
    ->setTipoOperacion('0101')
    ->setTipoDoc('03')
    ->setSerie($serie)
    ->setCorrelativo($correlativo)
    ->setFechaEmision(new DateTime())
    ->setTipoMoneda('PEN')
    ->setCompany($company)
    ->setClient($client)
    ->setMtoOperGravadas($subtotal)
    ->setMtoIGV($igv)
    ->setTotalImpuestos($igv)
    ->setValorVenta($subtotal)
    ->setSubTotal($total)
    ->setMtoImpVenta($total);

// 7. Agregar los productos del carrito
$details = [];
foreach ($items as $item) {
    $qty = floatval($item['quantity'] ?? 1);
    $precio = floatval($item['price'] ?? 0);
    $baseIgv = round($precio / 1.18, 2);
    $igvItem = round($precio - $baseIgv, 2);
    $valorVenta = round($baseIgv * $qty, 2);

    $detail = new SaleDetail();
    $detail->setCodProducto($item['code'] ?? 'P001')
        ->setUnidad($item['unit'] ?? 'NIU')
        ->setCantidad($qty)
        ->setDescripcion($item['description'] ?? $item['name'] ?? 'PRODUCTO')
        ->setMtoBaseIgv($valorVenta)
        ->setPorcentajeIgv(18.00)
        ->setIgv(round($igvItem * $qty, 2))
        ->setTotalImpuestos(round($igvItem * $qty, 2))
        ->setTipAfeIgv('10')
        ->setMtoValorVenta($valorVenta)
        ->setMtoPrecioUnitario($precio);
    $details[] = $detail;
}

$legend = new Legend();
$legend->setCode('1000')
    ->setValue(strtoupper($leyenda));

$invoice->setDetails($details)
    ->setLegends([$legend]);

// 8. Generar XML, limpiar el atributo problemático, y enviar a SUNAT
try {
    // Generar el XML firmado
    $xmlContent = $see->getXmlSigned($invoice);
    
    // PARCHE: Quitar el atributo languageLocaleID que SUNAT Beta rechaza
    $xmlContent = preg_replace('/ languageLocaleID="[^"]*"/', '', $xmlContent);
    
    // Obtener el nombre del archivo para SUNAT (ej: 20000000001-03-B001-1)
    $name = $ruc . '-03-' . $serie . '-' . $correlativo;
    
    // Enviar el XML limpio a SUNAT
    $res = $see->sendXml(get_class($invoice), $name, $xmlContent);

    if ($res->isSuccess()) {
        $cdr = $res->getCdrResponse();
        
        // Calcular hash del XML para el QR
        $hash = base64_encode(hash('sha256', $xmlContent, true));
        
        echo json_encode([
            "success" => true,
            "message" => "SUNAT aceptó la boleta.",
            "hash" => $hash,
            "cdrCode" => $cdr->getCode(),
            "cdrDescription" => $cdr->getDescription(),
            "serie" => $serie,
            "correlativo" => $correlativo
        ]);
    } else {
        $error = $res->getError();
        echo json_encode([
            "success" => false,
            "error" => $error ? $error->getMessage() : "Error desconocido de SUNAT.",
            "code" => $error ? $error->getCode() : null
        ]);
    }
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "error" => "Error interno: " . $e->getMessage()
    ]);
}

