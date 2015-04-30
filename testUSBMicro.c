/*************************************************************************/
// Example C code to (to port B) on U451 USB interface card
// Andrew Daviel advax [at] triumf.ca November 2012
//
// This code may be found at http://andrew.daviel.org/usbmicro
//
// This program will exit (failed to claim interface) unless it has
// write permission to the USB device. This may be achieved by running
// as root, setting this program suid root, setting world write in udev
// or setting ownership in udev (/etc/udev/rules.d). The last is the best option. 
//
// Some code taken from "General Linux Info" at http://www.usbmicro.com
// Some ideas taken from "usb_motion_driver.c" by Patrick M Geahan
//    at http://circuitgizmos.com/wordpress/?p=69
// U4xx commands taken from "Raw Device Programming" at http://www.usbmicro.com
//
// Compile with libusb, e.g. "gcc -lusb -o U451.write U451.write.c"
// Tested on Linux 2.6 (Fedora Core 9)
//
/*************************************************************************/

// Requires libusb version 0.1
#include <usb.h>
#include <stdio.h>

// U451
#define VENDOR_ID  0x0DE7
#define PRODUCT_ID 0x01C3

#define CANT_SEND -1
#define CANT_READ -2

// Find the particular device
static struct usb_device *find_U4xx( struct usb_bus *bus ) {
    struct usb_device *dev;
    // look through all busses
    for ( ; bus; bus = bus->next ) {
        // look at every device
        for ( dev = bus->devices; dev; dev = dev->next ) {
            // match to known IDs
            if ( dev->descriptor.idVendor == VENDOR_ID && dev->descriptor.idProduct == PRODUCT_ID )  return dev;
        }
    }
    return NULL;
}

// assemble control bytes into a character string
void buffer_set( char *buf, int a, int b, int c, int d, int e, int f, int g, int h ) {
    buf[0] = a; buf[1] = b; buf[2] = c; buf[3] = d; buf[4] = e;
    buf[5] = f; buf[6] = g; buf[7] = h;
}

// send the command string to the device
int send_command( struct usb_dev_handle *handle, char *command, int comLen, int resLen ) {
    //  handle, requesttype, request, value,  index, cmd bytes,  size, timeout
    int ret = usb_control_msg( handle, 0x21, 9, 0x0200, 0, command, comLen, 5000 );

    // check that send was successful
    if ( ret != comLen ) {
      printf ("Send failed, rcvd %d bytes not %d\n",ret,comLen) ;
      return CANT_SEND;
    }
    // does the command expect a result?
    if ( resLen > 0 ) {
               // handle, endpoint, cmd bytes, size, timeout
        ret = usb_bulk_read( handle, 0x81, command, resLen, 5000 );
        if ( ret != resLen ) {
          printf ("Read failed, rcvd %d bytes not %d\n",ret,resLen) ;
          return CANT_READ;
        }
    }
    return 0 ; 
}


int main(int argc, char *argv[]) {
    int busses, devices, ret, portA, portB;
    struct usb_bus *bus_list;
    struct usb_device *dev = NULL;
    struct usb_dev_handle *handle;
    char buffer[8];
    char dname[20] ;
    char string[256];
    int data ;

    // initialize the usb system
    usb_init();
    busses = usb_find_busses(); // update info on busses
    devices = usb_find_devices(); // update info on devices
    bus_list = usb_get_busses(); // get actual bus objects

    if ( ( dev = find_U4xx(bus_list) ) == NULL ) {
        printf ("Failed to find U4xx\n");
        return -1; // failure to find
    }
    printf("Found U451\n") ;

    if ( ( handle = usb_open(dev) ) == NULL) {
        printf ("Failed to open device\n");
        return -1; // failure to open
    }
    if (usb_get_driver_np(handle , 0, dname, 20) == 0) {
      printf("Detach driver %s\n",dname) ;
      if (usb_detach_kernel_driver_np(handle,0) ) {
        printf (" - Failed to detach kernel driver\n");
      }
    }  
    if (usb_claim_interface( handle, 0 ) ) {
      printf ("Failed to claim interface\n");
      usb_close(handle) ;
      handle = NULL;
      return -1; // failure to open
    }
    if (dev->descriptor.iSerialNumber) {
      if (usb_get_string_simple(handle, dev->descriptor.iSerialNumber, string, sizeof(string)))
        printf("Serial Number: %s\n",string) ;
    }
// get data byte to write in hex from command line
   if (argc < 2) {
     printf("Not enough arguments; expect hex data byte to write\n") ;
     return (-1) ;
   }
   sscanf(argv[1],"%x",&data);
   printf("data is 0x%x\n",data) ;

// set B to output (B has the relay drivers)
    buffer_set( buffer, 0x0A, 0xff, 0xff, 0, 0, 0, 0, 0 );
    if (send_command( handle, buffer, 8, 0 )) return -1; 

// write to B
    buffer_set( buffer, 0x02, data, 0, 0, 0, 0, 0, 0 );
    if (send_command( handle, buffer, 8, 0 )) return -1; 

    if ( usb_release_interface(handle, 0) || usb_close(handle) ) {
        printf ("Release interface failed\n") ;
        return -1; // report error
    }

    return 0; // success
}

