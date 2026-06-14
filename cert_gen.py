import os
import datetime
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def generate_self_signed_cert(ip_address="127.0.0.1", cert_name="cert.pem", key_name="key.pem"):
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    dir_path = os.path.join(appdata, "OpenCam", "certs")
    os.makedirs(dir_path, exist_ok=True)
    
    cert_path = os.path.join(dir_path, cert_name)
    key_path = os.path.join(dir_path, key_name)
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    print("Génération de certificats SSL auto-signés...")
    
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Generate public certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"OpenCam"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"OpenCam Local Server"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # Valid for 365 days to bypass iOS/macOS strict limits on self-signed certs
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.ip_address(ip_address))
        ]),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True,
    ).add_extension(
        x509.ExtendedKeyUsage([
            x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
        ]),
        critical=False,
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True,
    ).sign(private_key, hashes.SHA256())

    # Write key
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Write cert
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Certificats générés : {cert_path}, {key_path}")
    return cert_path, key_path

if __name__ == "__main__":
    generate_self_signed_cert()
