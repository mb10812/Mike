import dns.message
import dns.rdatatype
import dns.rdataclass
import dns.rdtypes
import dns.rdtypes.ANY
from dns.rdtypes.ANY.MX import MX
from dns.rdtypes.ANY.SOA import SOA
import dns.rdata
import dns.rrset
import socket
import threading
import signal
import os
import sys

import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import ast

# ---------------------------------------------------------------------------
# KEY DERIVATION
# ---------------------------------------------------------------------------
# PBKDF2HMAC stretches a human-readable password + random salt into a
# cryptographically strong 32-byte key, then base64url-encodes it so that
# Fernet (which expects a URL-safe base64 key) can consume it directly.
def generate_aes_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        iterations=100000,
        salt=salt,
        length=32
    )
    key = kdf.derive(password.encode('utf-8'))
    key = base64.urlsafe_b64encode(key)
    return key

# ---------------------------------------------------------------------------
# ENCRYPTION  (Fernet = AES-128-CBC + HMAC-SHA256 under the hood)
# ---------------------------------------------------------------------------
# Steps:
#   1. Derive the Fernet key from (password, salt).
#   2. Create a Fernet instance with that key.
#   3. Call f.encrypt() – it returns a base64url-encoded token (bytes).
def encrypt_with_aes(input_string, password, salt):
    key = generate_aes_key(password, salt)       # pass BOTH required args
    f = Fernet(key)                               # Fernet needs the b64 key
    encrypted_data = f.encrypt(input_string.encode('utf-8'))  # encrypt method
    return encrypted_data

# ---------------------------------------------------------------------------
# DECRYPTION
# ---------------------------------------------------------------------------
# Mirrors encryption exactly: same key derivation, then f.decrypt().
# decrypt() returns bytes, so we .decode() back to a plain string.
def decrypt_with_aes(encrypted_data, password, salt):
    key = generate_aes_key(password, salt)
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data)   # decrypt method
    return decrypted_data.decode('utf-8')

# ---------------------------------------------------------------------------
# DEMO VALUES
# ---------------------------------------------------------------------------
# salt  – must be a bytes object; os.urandom(16) is ideal in production,
#         but a fixed literal works fine for a classroom demo.
# password – any string; used purely for key derivation.
# input_string – the secret payload we want to "exfiltrate" via DNS TXT.
salt         = b'dns_lab_salt_16b'   # 16-byte literal salt
password     = 'SuperSecretPass123'
# The "exfiltrated" payload is the user's NYU email address.
# The test queries nyu.edu. IN TXT and expects to decrypt this value back out.
input_string = 'mb10812@nyu.edu'

encrypted_value = encrypt_with_aes(input_string, password, salt)   # exfil function
decrypted_value = decrypt_with_aes(encrypted_value, password, salt) # exfil function

# ---------------------------------------------------------------------------
# SHA-256 HELPER  (available for future use)
# ---------------------------------------------------------------------------
def generate_sha256_hash(input_string):
    sha256_hash = hashlib.sha256()
    sha256_hash.update(input_string.encode('utf-8'))
    return sha256_hash.hexdigest()

# ---------------------------------------------------------------------------
# DNS RECORD TABLE
# ---------------------------------------------------------------------------
# The encrypted payload is embedded in a TXT record for 'secret.example.com.'
# This is the data-exfiltration trick: TXT records can carry arbitrary
# base64-encoded blobs, making them a classic covert channel.
dns_records = {
    # ------------------------------------------------------------------
    # example.com. – original zone kept intact
    # ------------------------------------------------------------------
    'example.com.': {
        dns.rdatatype.A:    '192.168.1.101',
        dns.rdatatype.AAAA: '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
        dns.rdatatype.MX:   [(10, 'mail.example.com.')],
        dns.rdatatype.CNAME: 'www.example.com.',
        dns.rdatatype.NS:   'ns.example.com.',
        dns.rdatatype.TXT:  ('This is a TXT record',),
        dns.rdatatype.SOA:  (
            'ns1.example.com.',
            'admin.example.com.',
            2023081401,
            3600,
            1800,
            604800,
            86400,
        ),
    },

    # ------------------------------------------------------------------
    # safebank.com. – required by test_DNSServer_query
    # ------------------------------------------------------------------
    'safebank.com.': {
        dns.rdatatype.A: '192.168.1.201',
    },

    # ------------------------------------------------------------------
    # nyu.edu. – required by:
    #   • test_DNSServer_query      (A)
    #   • test_DNSServer_ipv6_query (AAAA)
    #   • test_DNSServer_MX_query   (MX)
    #   • test_DNSServer_NS_query   (NS)
    #   • test_exfiltrate           (TXT – encrypted email hidden here)
    #
    # The TXT record carries the Fernet-encrypted version of the user's
    # NYU email address.  The test decrypts it with the same password/salt
    # and verifies it matches the original.  This is the DNS exfiltration
    # covert channel: an observer just sees an opaque base64 blob.
    # ------------------------------------------------------------------
    'nyu.edu.': {
        dns.rdatatype.A:    '216.165.47.10',
        dns.rdatatype.AAAA: '2001:0db8:85a3:0000:0000:8a2e:0370:7334',
        dns.rdatatype.MX:   [(10, 'mail.nyu.edu.')],
        dns.rdatatype.NS:   'ns1.nyu.edu.',
        # Encrypted email stored as a TXT record – the exfiltration payload.
        # encrypted_value is Fernet bytes; decode to str for DNS wire format.
        dns.rdatatype.TXT:  (encrypted_value.decode('utf-8'),),
    },

    # Additional supporting records
    'mail.example.com.': {
        dns.rdatatype.A: '192.168.1.102',
    },
    'ns.example.com.': {
        dns.rdatatype.A: '192.168.1.103',
    },
    'mail.nyu.edu.': {
        dns.rdatatype.A: '216.165.47.11',
    },
    'ns1.nyu.edu.': {
        dns.rdatatype.A: '216.165.47.12',
    },
}

# ---------------------------------------------------------------------------
# DNS SERVER
# ---------------------------------------------------------------------------
def run_dns_server():
    # UDP socket – DNS almost always uses UDP (port 53); TCP is only for
    # zone transfers or responses > 512 bytes (EDNS0 aside).
    # socket.SOCK_DGRAM  → UDP datagram socket (vs SOCK_STREAM for TCP)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # '127.0.0.1' is the loopback address – the same "unique" local-only IP
    # used in the web-server lab.  Port 53 is the IANA-assigned DNS port.
    # NOTE: binding to port 53 requires root/admin privileges on most OSes.
    server_socket.bind(('127.0.0.1', 53))

    print("DNS server listening on 127.0.0.1:53 (UDP)")

    while True:
        try:
            # Receive up to 1024 bytes from any client
            data, addr = server_socket.recvfrom(1024)

            # dns.message.from_wire() deserialises the raw UDP payload into a
            # structured Message object we can inspect field-by-field.
            request = dns.message.from_wire(data)

            # make_response() copies the question section and sets QR=1 (reply)
            # while keeping the same message ID so the client matches it.
            response = dns.message.make_response(request)

            # A standard query carries exactly one question; index [0] gets it.
            question = request.question[0]
            qname = question.name.to_text()   # e.g. 'example.com.'
            qtype = question.rdtype           # e.g. dns.rdatatype.A (== 1)

            if qname in dns_records and qtype in dns_records[qname]:
                answer_data = dns_records[qname][qtype]
                rdata_list  = []

                if qtype == dns.rdatatype.MX:
                    # MX records carry a preference (priority) integer plus the
                    # mail-server name; the MX class constructor needs both.
                    for pref, server in answer_data:
                        rdata_list.append(
                            MX(dns.rdataclass.IN, dns.rdatatype.MX, pref, server)
                        )

                elif qtype == dns.rdatatype.SOA:
                    # Unpack all 7 SOA fields in the same order they appear in
                    # the dns_records tuple, then pass them straight to SOA().
                    mname, rname, serial, refresh, retry, expire, minimum = answer_data
                    rdata = SOA(
                        dns.rdataclass.IN, dns.rdatatype.SOA,
                        mname, rname, serial, refresh, retry, expire, minimum
                    )
                    rdata_list.append(rdata)

                else:
                    # For A, AAAA, CNAME, NS, TXT, etc., dns.rdata.from_text()
                    # handles the wire-format conversion generically.
                    if isinstance(answer_data, str):
                        rdata_list = [dns.rdata.from_text(dns.rdataclass.IN, qtype, answer_data)]
                    else:
                        rdata_list = [
                            dns.rdata.from_text(dns.rdataclass.IN, qtype, d)
                            for d in answer_data
                        ]

                # One RRset per (name, class, type) — all rdata go into it together.
                # The old pattern created a new RRset per rdata, leaving each one
                # with TTL=0 and a single record; dnspython's wire encoder then
                # silently dropped those answers. update_ttl() is required before
                # to_wire() will include the RRset in the answer section.
                rrset = dns.rrset.RRset(question.name, dns.rdataclass.IN, qtype)
                rrset.update_ttl(300)
                for rdata in rdata_list:
                    rrset.add(rdata)
                response.answer.append(rrset)

            # Set the AA (Authoritative Answer) bit – bit 10 of the flags field.
            # This tells the client our server is authoritative for the zone.
            response.flags |= 1 << 10

            # Serialise the response back to raw bytes with to_wire() and send
            # it back to the address we received the query from.
            print("Responding to request:", qname)
            server_socket.sendto(response.to_wire(), addr)

        except KeyboardInterrupt:
            print('\nExiting...')
            server_socket.close()
            sys.exit(0)


# ---------------------------------------------------------------------------
# ENTRY POINT WITH INTERACTIVE QUIT
# ---------------------------------------------------------------------------
def run_dns_server_user():
    print("Input 'q' and hit 'enter' to quit")
    print("DNS server is running...")

    def user_input():
        while True:
            cmd = input()
            if cmd.lower() == 'q':
                print('Quitting...')
                os.kill(os.getpid(), signal.SIGINT)

    input_thread = threading.Thread(target=user_input)
    input_thread.daemon = True
    input_thread.start()
    run_dns_server()


if __name__ == '__main__':
    run_dns_server_user()
    print("Encrypted Value:", encrypted_value)
    print("Decrypted Value:", decrypted_value)
