import time, options, log, sqlite3, ast, os, keys, base64
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP

config = options.Get()
config.read()
debug_level = config.debug_level_conf
ledger_path_conf = config.ledger_path_conf
full_ledger = config.full_ledger_conf
ledger_path = config.ledger_path_conf
hyper_path = config.hyper_path_conf


(key, private_key_readable, public_key_readable, public_key_hashed, address) = keys.read() #import keys
app_log = log.log("anon.log",debug_level)

def decrypt(encrypted):

    (cipher_aes_nonce, tag, ciphertext, enc_session_key) = ast.literal_eval(encrypted)
    private_key = RSA.import_key(open("privkey.der").read())
    # Decrypt the session key with the public RSA key
    cipher_rsa = PKCS1_OAEP.new(private_key)
    session_key = cipher_rsa.decrypt(enc_session_key)
    # Decrypt the data with the AES session key
    cipher_aes = AES.new(session_key, AES.MODE_EAX, cipher_aes_nonce)
    decrypted = cipher_aes.decrypt_and_verify(ciphertext, tag)
    return decrypted

def randomize(divider, anon_amount, anon_recipient, identifier, anon_sender):
    per_tx = int(anon_amount/divider) #how much per tx
    tx_count = int(anon_amount/per_tx) #how many txs
    remainder = anon_amount - per_tx*tx_count #remainder
    print(divider, tx_count, per_tx, remainder, identifier, anon_sender)

    anonymize(tx_count, per_tx, remainder, anon_recipient, identifier, anon_sender)
    return

def anonymize(tx_count, per_tx, remainder, anon_recipient, identifier, anon_sender):
    # return remainder to source!
    a.execute("SELECT * FROM transactions WHERE openfield = ?", (identifier,))
    try:
        exists = a.fetchall()[0]

    except:#if payout didn't happen yet
        print(tx_count, per_tx, remainder, identifier)
        for tx in range(tx_count):
            #construct tx
            openfield = "mixer"
            keep = 0
            fee = float('%.8f' % float(0.01 + (float(per_tx) * 0.001) + (float(len(openfield)) / 100000) + (float(keep) / 10)))  # 0.1% + 0.01 dust

            timestamp = '%.2f' % time.time()
            transaction = (str(timestamp), str(address), str(anon_recipient), '%.8f' % float(per_tx - fee), str(keep), str(openfield))  # this is signed
            # print transaction

            h = SHA.new(str(transaction).encode("utf-8"))
            signer = PKCS1_v1_5.new(key)
            signature = signer.sign(h)
            signature_enc = base64.b64encode(signature)
            print("Encoded Signature: {}".format(signature_enc.decode("utf-8")))

            verifier = PKCS1_v1_5.new(key)
            if verifier.verify(h, signature) == True:
                print("The signature is valid, proceeding to save transaction to mempool")
            #construct tx

            a.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)", (str(timestamp), str(address), str(anon_recipient), '%.8f' % float(per_tx - fee), str(signature_enc.decode("utf-8")), str(public_key_hashed), str(keep), str(identifier)))
            anon.commit()
            m.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)", (str(timestamp), str(address), str(anon_recipient), '%.8f' % float(per_tx - fee), str(signature_enc.decode("utf-8")), str(public_key_hashed), str(keep), str(openfield)))
            mempool.commit()


        if remainder - fee > 0:
            openfield = "mixer"
            keep = 0
            fee = float('%.8f' % float(0.01 + (float(remainder) * 0.001) + (float(len(openfield)) / 100000) + (float(keep) / 10)))  # 0.1% + 0.01 dust
            timestamp = '%.2f' % time.time()
            transaction = (str(timestamp), str(address), str(anon_sender), '%.8f' % float(remainder - fee), str(keep), str(openfield))  # this is signed
            m.execute("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?)", (str(timestamp), str(address), str(anon_sender), '%.8f' % float(remainder - fee), str(signature_enc.decode("utf-8")), str(public_key_hashed), str(keep), str(openfield)))
            mempool.commit()
    return

if not os.path.exists('anon.db'):
    # create empty mempool
    anon = sqlite3.connect('anon.db',timeout=1)
    anon.text_factory = str
    a = anon.cursor()
    a.execute("CREATE TABLE IF NOT EXISTS transactions (timestamp, address, recipient, amount, signature, public_key, keep, openfield)")
    anon.commit()
    print("Created anon file")

anon = sqlite3.connect('anon.db')
anon.text_factory = str
a = anon.cursor()

if full_ledger == 1:
    conn = sqlite3.connect(ledger_path)
else:
    conn = sqlite3.connect(hyper_path)

conn.text_factory = str
c = conn.cursor()

mempool = sqlite3.connect('mempool.db')
mempool.text_factory = str
m = mempool.cursor()

while True:
    try:
        for row in c.execute("SELECT * FROM transactions WHERE recipient = ? and openfield LIKE ? LIMIT 500", (address,)+("enc="+'%',)):
            anon_sender = row[2]

            try:
                #format: anon:number_of_txs:target_address (no msg, just encrypted)
                print (row)
                anon_recipient_encrypted = row[11].lstrip("enc=")
                print(anon_recipient_encrypted)
                anon_recipient = decrypt(anon_recipient_encrypted).decode("utf-8").split(":")[2]
                print(anon_recipient)
                divider = int(decrypt(anon_recipient_encrypted).decode("utf-8").split(":")[1])

                if len(anon_recipient) == 56:
                    anon_amount = float(row[4])
                    identifier = row[5][:8] #only save locally
                    #print (anon_sender, anon_recipient, anon_amount, identifier)

                    randomize(divider, float(anon_amount), anon_recipient, identifier, anon_sender)
                else:
                    print ("Wrong target address length")
            except Exception as e:
                print (e)

            #print("issue occured")
    except Exception as e:
        print (e)

    time.sleep(15)




