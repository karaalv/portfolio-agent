# Title

< Endpoint description, what it does and some context of when it is used >

<!-- General Info -->

---

* **URL:** `/path:required?optional`
* **Method:** `GET` | `POST` | `DELETE`
* **Authentication:** `None` | `JWT`
* **URL Parameters:**

  * `id` (string, required): User id for database retrieval.
* **Request Body:**

  ```json
  {
      "key": "<type>"
  }
  ```

<!-- Successful Responses -->

---

* **Successful Response:** Title

  * **Code:** `200`
  * **Response Object:**

    ```json
    {
        "key": "<type>"
    }
    ```

  * **Description:** < short description of successful response and intended state/actions >

<!-- Unsuccessful Responses -->

---

* **Unsuccessful Response:** Title 1

  <!-- Response 1 -->

  * **Code:** `500`
  * **Response Object:**

    ```json
    {
        "key": "<type>"
    }
    ```

  * **Description:** < short description of unsuccessful response and intended state/actions >
* **Unsuccessful Response:** Title 2

  <!-- Response 2 -->

  * **Code:** `400`
  * **Response Object:**

    ```json
    {
        "key": "<type>"
    }
    ```

  * **Description:** < short description of unsuccessful response and intended state/actions >

<!-- Notes -->

---

***Notes:*** < General notes or comments >
