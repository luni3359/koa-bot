-- Make users
CREATE USER 'admin'
    IDENTIFIED BY 'password';

-- Grant permissions
GRANT ALL
    ON *.*
    TO 'admin'
    WITH GRANT OPTION;

-- Example
-- CREATE USER 'admin'@'%.example.com'
--     IDENTIFIED BY 'password';
-- GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP
--     ON customer.addresses
--     TO 'custom'@'%.example.com';
