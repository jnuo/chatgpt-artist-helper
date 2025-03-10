import csv

def read_csv(file_path):
    """CSV dosyasını okur ve satırları bir liste olarak döndürür."""
    with open(file_path, "r", encoding="utf-8") as infile:
        return list(csv.DictReader(infile))

def write_csv(file_path, data, fieldnames):
    """CSV dosyasına yazma işlemi yapar."""
    with open(file_path, "w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
