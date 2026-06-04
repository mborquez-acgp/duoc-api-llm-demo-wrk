CREATE TABLE Customers (
    customer_id INT PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    customer_info VARCHAR(255) NOT NULL
);

CREATE TABLE Cards (
    card_id INT PRIMARY KEY,
    customer_id INT NOT NULL,
    card_number VARCHAR(20) NOT NULL,
    card_type VARCHAR(50) NOT NULL,
    operation_ammount_actual DECIMAL(15, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);

CREATE TABLE Transactions (
    transaction_id TEXT PRIMARY KEY,
    card_id INT NOT NULL,
    operation_date DATE NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    operation_ammount DECIMAL(15, 2) NOT NULL,
    operation_desc TEXT,
    FOREIGN KEY (card_id) REFERENCES Cards(card_id)
);
