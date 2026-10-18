<?xml version='1.0' encoding='UTF-8'?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
    <Script>
        <Name>airender\AirenderProva.py</Name>
        <Title>AIRENDER prova</Title>
        <Version>0.1</Version>
    </Script>
    <Page>
        <Name>Pagina</Name>
        <Text>AIRENDER</Text>
        <Parameters>
            <Parameter>
                <Name>Cartella</Name>
                <Text>Cartella viste (vuota = Usr\AIRENDER\viste)</Text>
                <Value></Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>UsaDimensione</Name>
                <Text>Dimensione immagine</Text>
                <Value>0</Value>
                <ValueType>RadioButtonGroup</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>DimensioneFinestra</Name>
                        <Text>come la finestra</Text>
                        <Value>0</Value>
                        <ValueType>RadioButton</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>DimensioneScelta</Name>
                        <Text>scelta (px)</Text>
                        <Value>1</Value>
                        <ValueType>RadioButton</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>Dimensione</Name>
                <Text>Larghezza | altezza (px)</Text>
                <Value>(1920|1080)</Value>
                <ValueType>tuple(Integer,Integer)</ValueType>
                <Visible>UsaDimensione == 1, UsaDimensione == 1</Visible>
            </Parameter>
            <Parameter>
                <Name>RigaCattura</Name>
                <Text>Finestra attiva</Text>
                <ValueType>Row</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>Cattura</Name>
                        <Text>Cattura vista</Text>
                        <EventId>1001</EventId>
                        <ValueType>Button</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>UltimaVista</Name>
                <Text>Ultima vista</Text>
                <Value></Value>
                <ValueType>String</ValueType>
                <Enable>False</Enable>
            </Parameter>
            <Parameter>
                <Name>Preset</Name>
                <Text>Preset</Text>
                <Value>base</Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>Testo</Name>
                <Text>Due parole tue</Text>
                <Value></Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>Destinazione</Name>
                <Text>L'immagine andra' a</Text>
                <Value></Value>
                <ValueType>String</ValueType>
                <Enable>False</Enable>
            </Parameter>
            <Parameter>
                <Name>RigaMotore</Name>
                <Text>Motore</Text>
                <ValueType>Row</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>ProvaASecco</Name>
                        <Text>Prova a secco</Text>
                        <EventId>1002</EventId>
                        <ValueType>Button</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>Genera</Name>
                        <Text>Genera render</Text>
                        <EventId>1003</EventId>
                        <ValueType>Button</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
        </Parameters>
    </Page>
</Element>
