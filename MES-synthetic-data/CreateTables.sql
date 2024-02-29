-- products Table
CREATE TABLE products (
    productid SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT
);

-- machines Table
CREATE TABLE machines (
    machineid SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),
    status VARCHAR(50) CHECK (status IN ('running', 'idle', 'maintenance'))
);

-- workorders Table
CREATE TABLE workorders (
    orderid SERIAL PRIMARY KEY,
    productid INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    startdate DATE,
    enddate DATE,
    status VARCHAR(50),
    FOREIGN KEY (productid) REFERENCES products(productid)
);

-- inventory
CREATE TABLE inventory (
    itemid SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL CHECK (quantity >= 0),
    reorderlevel INT NOT NULL CHECK (reorderlevel >= 0)
);

-- qualitycontrol Table
CREATE TABLE qualitycontrol (
    checkid SERIAL PRIMARY KEY,
    orderid INT NOT NULL,
    date DATE NOT NULL,
    result VARCHAR(50),
    comments TEXT,
    FOREIGN KEY (orderid) REFERENCES workorders(orderid)
);

-- employees Table
CREATE TABLE employees (
    employeeid SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    shift VARCHAR(50)
);
