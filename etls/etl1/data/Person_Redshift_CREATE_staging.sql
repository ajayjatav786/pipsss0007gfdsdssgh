CREATE TABLE staging.PERSON (
  "PersonID" int NOT NULL,
  "FirstName" varchar(100) DEFAULT NULL,
  "LastName" varchar(100) DEFAULT NULL,
  "MiddleName" varchar(50) DEFAULT NULL,
  "DateOfBirth" date DEFAULT NULL,
  "Suffix" varchar(50) DEFAULT NULL,
  "Prefix" varchar(50) DEFAULT NULL,
  "ActiveFlag" char(1) DEFAULT NULL,
  "CreateDate" datetime DEFAULT NULL,
  "UpdateDate" datetime DEFAULT NULL,
  "CreatedBy" varchar(50) DEFAULT NULL,
  "UpdatedBy" varchar(50) DEFAULT NULL,
  "GenderID" int DEFAULT NULL,
  PRIMARY KEY ("PersonID")
);
