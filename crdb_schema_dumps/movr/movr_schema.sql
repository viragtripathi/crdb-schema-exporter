-- TABLE: movr.users
CREATE TABLE public.users (
	id UUID NOT NULL,
	city VARCHAR NOT NULL,
	name VARCHAR NULL,
	address VARCHAR NULL,
	credit_card VARCHAR NULL,
	CONSTRAINT users_pkey PRIMARY KEY (city ASC, id ASC)
);


