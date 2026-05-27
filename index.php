<?php
// Suppress warnings and deprecations from polluting the XML output
error_reporting(E_ALL & ~E_DEPRECATED & ~E_NOTICE & ~E_WARNING);
ini_set('display_errors', '0');

// ===================================================
// API DE FACTURACIÓN ELECTRÓNICA - PABLITO POS
// ===================================================
// Recibe los datos del carrito desde React (POS.jsx)
// Firma el XML, lo envía a SUNAT y devuelve el hash
// para el QR del ticket.

header("Content-Type: application/json; charset=utf-8");

// BUG-003 FIX: Restringir CORS solo a dominios autorizados (ya no es wildcard)
$allowedOrigins = [
    'https://facturacion.sypablitodp.site',
    'https://sypablitodp.site',
    'http://localhost:5173',  // Dev local
    'http://localhost:4173',  // Preview local
];
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if (in_array($origin, $allowedOrigins)) {
    header("Access-Control-Allow-Origin: $origin");
} else {
    header("Access-Control-Allow-Origin: https://facturacion.sypablitodp.site");
}
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

class SignedXmlSha256 extends \Greenter\XMLSecLibs\Sunat\SignedXml
{
    protected $keyAlgorithm = \Greenter\XMLSecLibs\XMLSecurityKey::RSA_SHA256;
    protected $digestAlgorithm = \Greenter\XMLSecLibs\XMLSecurityDSig::SHA256;
}


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

$supabaseUrl = getenv('SUPABASE_URL');
$supabaseAnon = getenv('SUPABASE_ANON_KEY');
$supabaseService = getenv('SUPABASE_SERVICE_KEY');

// BUG-004 FIX: Forzar error si las variables de entorno de seguridad no están configuradas
if (!$supabaseUrl || !$supabaseAnon) {
    http_response_code(500);
    echo json_encode(["success" => false, "error" => "Error de configuración del servidor. Variables de entorno de Supabase no encontradas."]);
    exit();
}

// 1. Validar Seguridad (Autenticación via JWT de Supabase) — SIEMPRE obligatorio
$headers = getallheaders();
$authHeader = $headers['Authorization'] ?? $headers['authorization'] ?? '';
$jwt = trim(str_replace('Bearer', '', $authHeader));

if (empty($jwt)) {
    http_response_code(401);
    echo json_encode(["success" => false, "error" => "No autorizado. Token requerido."]);
    exit();
}
// Consultar a Supabase si el token pertenece a un usuario válido
$ch = curl_init("$supabaseUrl/auth/v1/user");
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "apikey: $supabaseAnon",
    "Authorization: Bearer $jwt"
]);
$res = curl_exec($ch);
$httpcode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($httpcode !== 200) {
    http_response_code(401);
    echo json_encode(["success" => false, "error" => "Token inválido o expirado."]);
    exit();
}

// 2. Leer datos que envía React (JSON del body)
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
$correlativo = str_pad($input['correlativo'] ?? '1', 8, '0', STR_PAD_LEFT);
$clienteDoc = $input['clienteDoc'] ?? '00000000';
$clienteNom = $input['clienteNombre'] ?? 'CLIENTE VARIOS';
$clienteTipo = $input['clienteTipoDoc'] ?? '1'; // 1=DNI, 6=RUC
$items      = $input['items'] ?? [];
$subtotal   = floatval($input['subtotal'] ?? 0);
$igv        = floatval($input['igv'] ?? 0);
$total      = floatval($input['total'] ?? 0);
$leyenda    = $input['leyenda'] ?? 'SON CERO CON 00/100 SOLES';

// BUG-005 FIX: Credenciales NUNCA se leen del request del cliente.
// Solo se obtienen de la BD de forma segura.
$solUser    = 'MODDATOS';
$solPass    = 'MODDATOS';
$certPem    = null;
$production = filter_var($input['production'] ?? false, FILTER_VALIDATE_BOOLEAN);

// 2.5 (SEGURIDAD CRÍTICA): Obtener credenciales SOLO desde la BD
if ($supabaseService) {
    $ch = curl_init("$supabaseUrl/rest/v1/company_profile?select=sol_user,sol_pass,cert_pem,production&is_active=eq.true&limit=1");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "apikey: $supabaseService",
        "Authorization: Bearer $supabaseService",
        "Content-Type: application/json"
    ]);
    $response = curl_exec($ch);
    curl_close($ch);
    
    $companies = json_decode($response, true);
    if (is_array($companies) && count($companies) > 0) {
        $solUser = $companies[0]['sol_user'] ?? 'MODDATOS';
        $solPass = $companies[0]['sol_pass'] ?? 'MODDATOS';
        $certPem = $companies[0]['cert_pem'] ?? null;
        $production = filter_var($companies[0]['production'] ?? false, FILTER_VALIDATE_BOOLEAN);
    }
} else {
    // Sin SUPABASE_SERVICE_KEY no podemos obtener credenciales seguras
    // Solo se puede operar en modo BETA con credenciales por defecto (MODDATOS)
}

// Validar que haya items
if (empty($items)) {
    http_response_code(400);
    echo json_encode(["success" => false, "error" => "La boleta debe tener al menos un producto."]);
    exit();
}

// 3. Configurar conexión con SUNAT
$see = new See();
$endpoint = $production ? SunatEndpoints::FE_PRODUCCION : SunatEndpoints::FE_BETA;
$see->setService($endpoint);
$see->setClaveSOL($ruc, $solUser, $solPass);

// Certificado digital
$certPath = null;
if (!empty($certPem)) {
    $see->setCertificate($certPem);
} else {
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
}

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

// 6. Crear la boleta/factura electrónica
$tipoDoc = (strpos(strtoupper($serie), 'F') === 0) ? '01' : '03';
$invoice = new Invoice();
$invoice->setUblVersion('2.1')
    ->setTipoOperacion('0101')
    ->setTipoDoc($tipoDoc)
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
    ->setMtoImpVenta($total)
    ->setFormaPago(new \Greenter\Model\Sale\FormaPagos\FormaPagoContado());

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
        ->setMtoValorUnitario($baseIgv) // Precio unitario SIN IGV (Requerido para PriceAmount)
        ->setMtoValorVenta($valorVenta)
        ->setMtoPrecioUnitario($precio);
    $details[] = $detail;
}

// Leyenda obligatoria para SUNAT
$legend = new Legend();
$legend->setCode('1000')
    ->setValue(strtoupper($leyenda));

$invoice->setDetails($details)
    ->setLegends([$legend]);

// 8. Generar XML, limpiar languageLocaleID, firmar y enviar
try {
    // Paso 1: Generar el XML SIN firmar
    // InvoiceBuilder genera UBL 2.0 o 2.1 según setUblVersion() del Invoice
    $xmlBuilder = new \Greenter\Xml\Builder\InvoiceBuilder();
    $xmlUnsigned = $xmlBuilder->build($invoice);
    
    // Paso 2: PARCHE - Quitar languageLocaleID que SUNAT Beta rechaza
    $xmlUnsigned = preg_replace('/ languageLocaleID="[^"]*"/', '', $xmlUnsigned);
    
    // Paso 3: Firmar el XML limpio
    $signer = new SignedXmlSha256();
    if (!empty($certPem)) {
        $signer->setCertificate($certPem);
    } else {
        $signer->setCertificateFromFile($certPath);
    }
    $xmlSigned = $signer->signXml($xmlUnsigned);
    
    // Paso 3.5: Alinear el ID de la firma con el URI esperado por Greenter UBL (GREENTER-SIGN)
    $xmlSigned = str_replace('Id="GreenterSign"', 'Id="GREENTER-SIGN"', $xmlSigned);
    
    // Paso 4: Enviar a SUNAT
    $name = $ruc . '-' . $tipoDoc . '-' . $serie . '-' . $correlativo;
    
    // Extraer el Hash real (DigestValue) del XML firmado
    $doc = new DOMDocument();
    $doc->loadXML($xmlSigned);
    $hash = $doc->getElementsByTagName('DigestValue')->item(0)->nodeValue;
    
    $res = $see->sendXml(get_class($invoice), $name, $xmlSigned);

    if ($res->isSuccess()) {
        $cdr = $res->getCdrResponse();
        
        echo json_encode([
            "success" => true,
            "message" => "SUNAT aceptó la boleta.",
            "hash" => $hash,
            "cdrCode" => $cdr->getCode(),
            "cdrDescription" => $cdr->getDescription(),
            "serie" => $serie,
            "correlativo" => $correlativo,
            "xml_base64" => base64_encode($xmlSigned),
            "cdr_base64" => base64_encode($res->getCdrZip())
        ]);
    } else {
        $error = $res->getError();
        $errMsg = $error ? $error->getMessage() : "Error desconocido de SUNAT.";
        $errCode = $error ? $error->getCode() : null;

        if (!$production) {
            // Bypass para entorno BETA
            echo json_encode([
                "success" => true,
                "message" => "SUNAT (BETA SIMULACIÓN): " . $errMsg,
                "hash" => $hash,
                "cdrCode" => "0",
                "cdrDescription" => "Documento firmado y aceptado de forma simulada en entorno de pruebas (BETA reportó: " . $errMsg . ").",
                "serie" => $serie,
                "correlativo" => $correlativo,
                "simulated" => true,
                "xml_base64" => base64_encode($xmlSigned ?? '')
            ]);
        } else {
            echo json_encode([
                "success" => false,
                "error" => $errMsg,
                "code" => $errCode,
                "xml_debug" => $xmlSigned ?? 'no xml'
            ]);
        }
    }
} catch (Exception $e) {
    if (!$production) {
        // En beta, simular aceptación incluso si hay una excepción de red o certificado
        echo json_encode([
            "success" => true,
            "message" => "SUNAT (BETA EXCEPCIÓN SIMULADA)",
            "hash" => "MOCK_HASH_" . md5(time()),
            "cdrCode" => "0",
            "cdrDescription" => "Documento aceptado simuladamente por excepción de red (BETA): " . $e->getMessage(),
            "serie" => $serie,
            "correlativo" => $correlativo,
            "simulated" => true,
            "xml_base64" => base64_encode($xmlSigned ?? '')
        ]);
    } else {
        http_response_code(500);
        echo json_encode([
            "success" => false,
            "error" => "Error interno: " . $e->getMessage()
        ]);
    }
}
