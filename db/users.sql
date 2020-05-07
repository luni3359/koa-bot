-- Make users
CREATE USER 'luni3359'
    IDENTIFIED BY 'password';

-- Grant permissions
GRANT ALL
    ON *.*
    TO 'luni3359'
    WITH GRANT OPTION;

-- Example
-- CREATE USER 'luni3359'@'%.example.com'
--     IDENTIFIED BY 'password';
-- GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP
--     ON customer.addresses
--     TO 'custom'@'%.example.com';
